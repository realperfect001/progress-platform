from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.constants import PENDING_STATUSES
from app.models.correction import Correction
from app.models.project import Project
from app.models.student import Student
from app.models.submission import Submission
from app.models.user import User
from app.services.notifications import recent_notifications
from app.services.progress import get_progress
from app.services.project_service import overview_rows


def student_dashboard(db: Session, user: User) -> dict:
    notifications = recent_notifications(db, user)
    project = db.scalar(select(Project).where(Project.student_id == user.user_id))
    if project is None:
        return {
            "project": None,
            "percent_complete": 0.0,
            "health": None,
            "chapters": [],
            "needs_attention": [],
            "recent_notifications": notifications,
        }
    progress = get_progress(db, project)
    return {
        "project": project,
        "percent_complete": progress["percent_complete"],
        "health": progress["health"],
        "chapters": progress["chapters"],
        "needs_attention": [c for c in progress["chapters"] if c["status"] == "needs_revision"],
        "recent_notifications": notifications,
    }


def supervisor_dashboard(db: Session, user: User) -> dict:
    rows = overview_rows(db, supervisor_id=user.user_id)

    queue, awaiting, needs_revision = [], 0, 0
    for row in rows:
        for chapter in row["chapters"]:
            if chapter["status"] in PENDING_STATUSES:
                awaiting += 1
                queue.append(
                    {
                        "submission_id": chapter["submission_id"],
                        "project_id": row["project_id"],
                        "student_id": row["student_id"],
                        "student_name": row["full_name"],
                        "matric_no": row["matric_no"],
                        "chapter_no": chapter["chapter_no"],
                        "version": chapter["version"],
                        "status": chapter["status"],
                        "date_submitted": chapter["date_submitted"],
                    }
                )
            elif chapter["status"] == "needs_revision":
                needs_revision += 1
    queue.sort(key=lambda item: item["date_submitted"])  # oldest first

    at_risk = sorted(
        (r for r in rows if r["health"] == "delayed"), key=lambda r: r["percent_complete"]
    )

    activity = []
    submissions = db.execute(
        select(Submission, User.full_name)
        .join(Project, Project.project_id == Submission.project_id)
        .join(Student, Student.student_id == Project.student_id)
        .join(User, User.user_id == Student.student_id)
        .where(Student.supervisor_id == user.user_id)
        .order_by(Submission.date_submitted.desc())
        .limit(10)
    ).all()
    for submission, name in submissions:
        activity.append(
            {
                "type": "submission",
                "message": f"{name} submitted Chapter {submission.chapter_no} "
                f"(version {submission.version})",
                "related_type": "submission",
                "related_id": submission.submission_id,
                "date": submission.date_submitted,
            }
        )
    corrections = db.execute(
        select(Correction, Submission.chapter_no, User.full_name)
        .join(Submission, Submission.submission_id == Correction.submission_id)
        .join(Project, Project.project_id == Submission.project_id)
        .join(User, User.user_id == Project.student_id)
        .where(Correction.supervisor_id == user.user_id)
        .order_by(Correction.date_created.desc())
        .limit(10)
    ).all()
    for correction, chapter_no, name in corrections:
        activity.append(
            {
                "type": "correction",
                "message": f"You commented on {name}'s Chapter {chapter_no}",
                "related_type": "submission",
                "related_id": correction.submission_id,
                "date": correction.date_created,
            }
        )
    activity.sort(key=lambda a: a["date"], reverse=True)

    return {
        "counts": {
            "students": len(rows),
            "awaiting_review": awaiting,
            "needs_revision": needs_revision,
            "delayed": len(at_risk),
        },
        "review_queue": queue[:20],
        "at_risk": at_risk,
        "recent_activity": activity[:10],
    }


def admin_dashboard(db: Session) -> dict:
    def count(role: str) -> int:
        return db.scalar(select(func.count()).select_from(User).where(User.role == role)) or 0

    rows = overview_rows(db)
    with_project = [r for r in rows if r["project_id"] is not None]

    by_supervisor = []
    supervisors = db.scalars(
        select(User).where(User.role == "supervisor").order_by(User.full_name)
    ).all()
    for supervisor in supervisors:
        mine = [r for r in rows if r["supervisor_id"] == supervisor.user_id]
        average = sum(r["percent_complete"] for r in mine) / len(mine) if mine else 0.0
        by_supervisor.append(
            {
                "supervisor_id": supervisor.user_id,
                "full_name": supervisor.full_name,
                "students": len(mine),
                "average_percent": round(average, 1),
                "delayed": sum(1 for r in mine if r["health"] == "delayed"),
            }
        )

    return {
        "totals": {
            "students": count("student"),
            "supervisors": count("supervisor"),
            "projects": len(with_project),
        },
        "progress_by_supervisor": by_supervisor,
        "delayed_projects": [r for r in with_project if r["health"] == "delayed"],
    }
