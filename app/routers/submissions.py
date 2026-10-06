from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from app.core.deps import CurrentUser, DbSession, require_role
from app.core.pagination import PageParams
from app.models.user import User
from app.schemas.common import Page
from app.schemas.submissions import (
    CorrectionIn,
    CorrectionOut,
    StatusIn,
    SubmissionCreated,
    SubmissionListItem,
    SubmissionOut,
)
from app.services import correction_service, submission_service

router = APIRouter(tags=["submissions"])

StudentUser = Annotated[User, Depends(require_role("student"))]
SupervisorUser = Annotated[User, Depends(require_role("supervisor"))]


@router.post(
    "/projects/{project_id}/submissions", response_model=SubmissionCreated, status_code=201
)
def create_submission(
    project_id: int,
    user: StudentUser,
    db: DbSession,
    chapter_no: Annotated[int, Form()],
    file: Annotated[UploadFile | None, File()] = None,
    content: Annotated[str | None, Form()] = None,
    note: Annotated[str | None, Form()] = None,
):
    return submission_service.create_submission(
        db, user, project_id, chapter_no, file, content, note
    )


@router.get("/projects/{project_id}/submissions", response_model=Page[SubmissionListItem])
def list_submissions(
    project_id: int,
    user: CurrentUser,
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    chapter_no: int | None = None,
    status: str | None = None,
    sort: str | None = None,
):
    return submission_service.list_submissions(
        db, user, project_id, chapter_no, status, params, sort
    )


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: int, user: CurrentUser, db: DbSession):
    return submission_service.open_submission(db, user, submission_id)


@router.get("/submissions/{submission_id}/file", response_class=FileResponse)
def download_file(submission_id: int, user: CurrentUser, db: DbSession):
    submission, path = submission_service.get_file_path(db, user, submission_id)
    return FileResponse(
        path,
        media_type=submission.mime_type or "application/octet-stream",
        filename=submission.file_name or "download",
        content_disposition_type="attachment",
    )


@router.get("/submissions/{submission_id}/corrections", response_model=list[CorrectionOut])
def list_corrections(submission_id: int, user: CurrentUser, db: DbSession):
    return correction_service.list_corrections(db, user, submission_id)


@router.post(
    "/submissions/{submission_id}/corrections", response_model=CorrectionOut, status_code=201
)
def add_correction(submission_id: int, data: CorrectionIn, user: SupervisorUser, db: DbSession):
    return correction_service.add_correction(db, user, submission_id, data.comment)


@router.patch("/submissions/{submission_id}/status", response_model=SubmissionOut)
def change_status(submission_id: int, data: StatusIn, user: SupervisorUser, db: DbSession):
    return correction_service.set_status(db, user, submission_id, data.status)
