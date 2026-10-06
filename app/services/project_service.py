from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.core.errors import AppError
from app.core.pagination import PageParams, paginate_list, sort_rows
from app.db.base import utcnow
from app.models.project import Project
from app.models.student import Student
from app.models.user import User
from app.services.access import get_project_or_404
from app.services.progress import progress_for_projects


def create_project(db: Session, user: User, title: str) -> Project:
    if db.scalar(select(Project.project_id).where(Project.student_id == user.user_id)):
        raise AppError(409, "You already have a project")
    project = Project(student_id=user.user_id, title=title, status="not_started")
    db.add(project)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "You already have a project")
    return project


def get_my_project(db: Session, user: User) -> Project:
    project = db.scalar(select(Project).where(Project.student_id == user.user_id))
    if project is None:
        raise AppError(404, "You have not created a project yet")
    return project


def update_project(db: Session, user: User, project_id: int, title: str) -> Project:
    project = get_project_or_404(db, user, project_id)
    if project.student_id != user.user_id:
        raise AppError(404, "Project not found")
    project.title = title
    project.updated_at = utcnow()
    db.commit()
    return project


def overview_rows(
    db: Session,
    *,
    supervisor_id: int | None = None,
    search: str | None = None,
    require_project: bool = False,
) -> list[dict]:
    """One row per student with project and progress. Health is derived, so it is filtered in Python."""
    supervisor = aliased(User)
    stmt = (
        select(Student, User, Project, supervisor)
        .join(User, User.user_id == Student.student_id)
        .join(Project, Project.student_id == Student.student_id, isouter=not require_project)
        .join(supervisor, supervisor.user_id == Student.supervisor_id, isouter=True)
    )
    if supervisor_id is not None:
        stmt = stmt.where(Student.supervisor_id == supervisor_id)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            User.full_name.ilike(pattern)
            | Student.matric_no.ilike(pattern)
            | Project.title.ilike(pattern)
        )
    records = db.execute(stmt).all()
    progress = progress_for_projects(db, [r[2] for r in records if r[2] is not None])

    rows = []
    for student, user, project, sup in records:
        p = progress.get(project.project_id) if project else None
        rows.append(
            {
                "student_id": student.student_id,
                "full_name": user.full_name,
                "student_name": user.full_name,
                "matric_no": student.matric_no,
                "supervisor_id": sup.user_id if sup else None,
                "supervisor_name": sup.full_name if sup else None,
                "project_id": project.project_id if project else None,
                "title": project.title if project else None,
                "status": p["status"] if p else "not_started",
                "date_created": project.date_created if project else None,
                "updated_at": project.updated_at if project else None,
                "percent_complete": p["percent_complete"] if p else 0.0,
                "health": p["health"] if p else None,
                "last_submission_at": p["last_submission_at"] if p else None,
                "chapters": p["chapters"] if p else [],
            }
        )
    return rows


def supervisor_students(
    db: Session,
    user: User,
    search: str | None,
    health: str | None,
    params: PageParams,
    sort: str | None,
) -> dict:
    rows = overview_rows(db, supervisor_id=user.user_id, search=search)
    if health:
        rows = [r for r in rows if r["health"] == health]
    rows = sort_rows(
        rows,
        sort,
        {"full_name", "matric_no", "percent_complete", "last_submission_at"},
        "full_name",
    )
    return paginate_list(rows, params)


def admin_projects(
    db: Session,
    supervisor_id: int | None,
    status: str | None,
    health: str | None,
    search: str | None,
    params: PageParams,
    sort: str | None,
) -> dict:
    rows = overview_rows(db, supervisor_id=supervisor_id, search=search, require_project=True)
    if status:
        rows = [r for r in rows if r["status"] == status]
    if health:
        rows = [r for r in rows if r["health"] == health]
    rows = sort_rows(
        rows,
        sort,
        {"student_name", "title", "percent_complete", "date_created", "updated_at"},
        "-updated_at",
    )
    return paginate_list(rows, params)


def student_detail(db: Session, student: Student) -> dict:
    project = student.project
    project_data = None
    if project is not None:
        p = progress_for_projects(db, [project])[project.project_id]
        project_data = {
            "project_id": project.project_id,
            "student_id": project.student_id,
            "title": project.title,
            "status": p["status"],
            "date_created": project.date_created,
            "updated_at": project.updated_at,
            "percent_complete": p["percent_complete"],
            "health": p["health"],
        }
    return {
        "student_id": student.student_id,
        "full_name": student.user.full_name,
        "email": student.user.email,
        "matric_no": student.matric_no,
        "department": student.department,
        "supervisor": student.supervisor,
        "project": project_data,
    }


def get_student_detail(db: Session, user: User, student_id: int) -> dict:
    student = db.get(Student, student_id)
    if student is None or (user.role == "supervisor" and student.supervisor_id != user.user_id):
        raise AppError(404, "Student not found")
    return student_detail(db, student)
