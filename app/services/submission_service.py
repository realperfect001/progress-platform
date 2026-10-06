from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, field_error
from app.core.pagination import PageParams, apply_sort, paginate_scalars
from app.models.constants import PENDING_STATUSES, SUBMISSION_STATUSES
from app.models.project import Project
from app.models.submission import Submission
from app.models.user import User
from app.services.access import get_project_or_404, get_submission_or_404
from app.services.notifications import notify
from app.services.progress import sync_project_status
from app.storage.files import delete_file, resolve_path, save_upload

MAX_TEXT_CHARS = 200_000
MAX_NOTE_CHARS = 2_000


def create_submission(
    db: Session,
    user: User,
    project_id: int,
    chapter_no: int,
    upload: UploadFile | None,
    content: str | None,
    note: str | None,
) -> Submission:
    project = db.scalar(select(Project).where(Project.student_id == user.user_id))
    if project is None:
        raise AppError(400, "Create your project before submitting a chapter")  # rule 1
    if project.project_id != project_id:
        raise AppError(404, "Project not found")
    if not 1 <= chapter_no <= settings.TOTAL_CHAPTERS:
        raise field_error("chapter_no", f"Chapter must be between 1 and {settings.TOTAL_CHAPTERS}")

    has_file = upload is not None and bool(upload.filename)
    text = content if content and content.strip() else None
    if has_file and text:
        raise AppError(400, "Send either a file or text content, not both")  # rule 4
    if not has_file and not text:
        raise AppError(400, "Send a file or text content")
    if text and len(text) > MAX_TEXT_CHARS:
        raise field_error("content", "The text is too long; upload a file instead")
    note = note.strip() if note and note.strip() else None
    if note and len(note) > MAX_NOTE_CHARS:
        raise field_error("note", f"The note must be at most {MAX_NOTE_CHARS} characters")

    latest = db.scalar(
        select(Submission)
        .where(Submission.project_id == project.project_id, Submission.chapter_no == chapter_no)
        .order_by(Submission.version.desc())
        .limit(1)
    )
    if latest is not None:
        if latest.status == "approved":  # rule 3
            raise AppError(409, f"Chapter {chapter_no} is already approved")
        if latest.status in PENDING_STATUSES:  # rule 2
            raise AppError(409, f"Chapter {chapter_no} already has a version waiting for review")

    stored = save_upload(upload) if has_file else None
    submission = Submission(
        project_id=project.project_id,
        chapter_no=chapter_no,
        version=latest.version + 1 if latest else 1,
        content=text,
        file_name=stored.file_name if stored else None,
        file_path=stored.stored_name if stored else None,
        mime_type=stored.mime_type if stored else None,
        file_size=stored.size if stored else None,
        note=note,
        status="submitted",
    )
    db.add(submission)
    try:
        db.flush()
        sync_project_status(db, project)
        supervisor_id = project.student.supervisor_id
        if supervisor_id is not None:
            notify(
                db,
                supervisor_id,
                f"{user.full_name} submitted Chapter {chapter_no} (version {submission.version})",
                "submission_received",
                "submission",
                submission.submission_id,
            )
        db.commit()
    except IntegrityError:
        db.rollback()
        delete_file(stored.stored_name if stored else None)
        raise AppError(409, f"Chapter {chapter_no} already has a version waiting for review")
    except Exception:
        db.rollback()
        delete_file(stored.stored_name if stored else None)
        raise
    return submission


def list_submissions(
    db: Session,
    user: User,
    project_id: int,
    chapter_no: int | None,
    status: str | None,
    params: PageParams,
    sort: str | None,
):
    project = get_project_or_404(db, user, project_id)
    stmt = select(Submission).where(Submission.project_id == project.project_id)
    if chapter_no is not None:
        stmt = stmt.where(Submission.chapter_no == chapter_no)
    if status:
        if status not in SUBMISSION_STATUSES:
            raise field_error("status", f"Status must be one of: {', '.join(SUBMISSION_STATUSES)}")
        stmt = stmt.where(Submission.status == status)
    stmt = apply_sort(
        stmt,
        sort,
        {
            "date_submitted": Submission.date_submitted,
            "chapter_no": Submission.chapter_no,
            "version": Submission.version,
            "status": Submission.status,
        },
        "-date_submitted",
    )
    return paginate_scalars(db, stmt, params)


def open_submission(db: Session, user: User, submission_id: int) -> Submission:
    """Returns a visible submission. The assigned supervisor opening it first moves it to under_review."""
    submission = get_submission_or_404(db, user, submission_id)
    if user.role == "supervisor" and submission.status == "submitted":
        submission.status = "under_review"
        db.commit()
    return submission


def get_file_path(db: Session, user: User, submission_id: int):
    submission = open_submission(db, user, submission_id)
    if not submission.file_path:
        raise AppError(404, "This submission has no file")
    return submission, resolve_path(submission.file_path)
