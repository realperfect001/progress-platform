from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.errors import AppError, field_error
from app.core.pagination import PageParams, apply_sort, paginate_scalars
from app.models.chapter_schedule import ChapterSchedule
from app.models.constants import ROLES
from app.models.student import Student
from app.models.user import User
from app.schemas.admin import ScheduleItem
from app.services.auth_service import revoke_user_refresh_tokens
from app.services.notifications import notify
from app.services.project_service import student_detail


def list_users(db: Session, role: str | None, search: str | None, params: PageParams, sort: str | None):
    stmt = select(User).options(selectinload(User.student).selectinload(Student.supervisor))
    if role:
        if role not in ROLES:
            raise field_error("role", f"Role must be one of: {', '.join(ROLES)}")
        stmt = stmt.where(User.role == role)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        stmt = stmt.join(Student, Student.student_id == User.user_id, isouter=True).where(
            or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                Student.matric_no.ilike(pattern),
            )
        )
    stmt = apply_sort(
        stmt,
        sort,
        {"full_name": User.full_name, "email": User.email, "created_at": User.created_at},
        "full_name",
    )
    return paginate_scalars(db, stmt, params)


def update_user(
    db: Session, admin: User, user_id: int, is_active: bool | None, is_approved: bool | None
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "User not found")
    if is_active is False and user.user_id == admin.user_id:
        raise AppError(400, "You cannot deactivate your own account")
    if is_active is not None:
        user.is_active = is_active
        if not is_active:
            revoke_user_refresh_tokens(db, user.user_id)
    if is_approved is not None:
        newly_approved = is_approved and not user.is_approved
        user.is_approved = is_approved
        if newly_approved and user.role == "supervisor":
            notify(db, user.user_id, "Your account is approved", "account_approved", "user", user.user_id)
    db.commit()
    return user


def assign_supervisor(db: Session, student_id: int, supervisor_id: int) -> dict:
    student = db.get(Student, student_id)
    if student is None:
        raise AppError(404, "Student not found")
    supervisor = db.get(User, supervisor_id)
    if (
        supervisor is None
        or supervisor.role != "supervisor"
        or not supervisor.is_active
        or not supervisor.is_approved
    ):
        raise field_error("supervisor_id", "Choose an approved, active supervisor")
    if student.supervisor_id != supervisor.user_id:
        student.supervisor_id = supervisor.user_id
        notify(
            db,
            student.student_id,
            f"You have been assigned to {supervisor.full_name}",
            "supervisor_assigned",
            "user",
            supervisor.user_id,
        )
        notify(
            db,
            supervisor.user_id,
            f"{student.user.full_name} has been assigned to you",
            "student_assigned",
            "user",
            student.student_id,
        )
        db.commit()
        db.refresh(student)
    return student_detail(db, student)


def get_schedule(db: Session) -> list[ChapterSchedule]:
    return list(db.scalars(select(ChapterSchedule).order_by(ChapterSchedule.chapter_no)))


def replace_schedule(db: Session, items: list[ScheduleItem]) -> list[ChapterSchedule]:
    numbers = [i.chapter_no for i in items]
    if len(set(numbers)) != len(numbers):
        raise field_error("chapters", "Each chapter can appear only once")
    if any(not 1 <= n <= settings.TOTAL_CHAPTERS for n in numbers):
        raise field_error("chapters", f"Chapters must be between 1 and {settings.TOTAL_CHAPTERS}")
    existing = {row.chapter_no: row for row in get_schedule(db)}
    for number, row in existing.items():
        if number not in numbers:
            db.delete(row)
    for item in items:
        if item.chapter_no in existing:
            existing[item.chapter_no].due_date = item.due_date
        else:
            db.add(ChapterSchedule(chapter_no=item.chapter_no, due_date=item.due_date))
    db.commit()
    return get_schedule(db)
