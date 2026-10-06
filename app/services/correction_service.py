from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.constants import PENDING_STATUSES
from app.models.correction import Correction
from app.models.submission import Submission
from app.models.user import User
from app.services.access import get_submission_or_404
from app.services.notifications import notify
from app.services.progress import sync_project_status


def list_corrections(db: Session, user: User, submission_id: int) -> list[Correction]:
    submission = get_submission_or_404(db, user, submission_id)
    return list(
        db.scalars(
            select(Correction)
            .where(Correction.submission_id == submission.submission_id)
            .order_by(Correction.date_created.desc(), Correction.correction_id.desc())
        )
    )


def add_correction(db: Session, user: User, submission_id: int, comment: str) -> Correction:
    # The route allows supervisors only; get_submission_or_404 returns 404 unless this
    # supervisor is the student's assigned supervisor (rule 5).
    submission = get_submission_or_404(db, user, submission_id)
    if submission.status == "approved":  # rule 7
        raise AppError(409, "Corrections cannot be added to an approved submission")
    correction = Correction(
        submission_id=submission.submission_id, supervisor_id=user.user_id, comment=comment
    )
    db.add(correction)
    if submission.status == "submitted":
        submission.status = "under_review"
    db.commit()
    return correction


def set_status(db: Session, user: User, submission_id: int, new_status: str) -> Submission:
    submission = get_submission_or_404(db, user, submission_id)
    if submission.status not in PENDING_STATUSES:
        label = submission.status.replace("_", " ")
        raise AppError(409, f"A submission that is {label} cannot change status")

    count = (
        db.scalar(
            select(func.count())
            .select_from(Correction)
            .where(Correction.submission_id == submission.submission_id)
        )
        or 0
    )
    if new_status == "needs_revision" and count == 0:  # rule 6
        raise AppError(400, "Add at least one correction before requesting a revision")

    submission.status = new_status
    project = submission.project
    db.flush()
    sync_project_status(db, project)

    chapter = f"Chapter {submission.chapter_no}"
    student_id = project.student_id
    if new_status == "needs_revision":
        plural = "correction" if count == 1 else "corrections"
        notify(
            db,
            student_id,
            f"{chapter} needs revision ({count} {plural})",
            "revision_requested",
            "submission",
            submission.submission_id,
        )
    else:
        notify(
            db,
            student_id,
            f"{chapter} was approved",
            "chapter_approved",
            "submission",
            submission.submission_id,
        )
        if project.status == "completed":
            notify(
                db,
                student_id,
                "Project completed: all chapters are approved",
                "project_completed",
                "project",
                project.project_id,
            )
            notify(
                db,
                user.user_id,
                f"{project.student.user.full_name}'s project is completed",
                "project_completed",
                "project",
                project.project_id,
            )
    db.commit()
    return submission
