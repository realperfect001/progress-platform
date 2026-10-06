from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

from app.schemas.common import ORMModel


class SubmissionCreated(ORMModel):
    submission_id: int
    chapter_no: int
    version: int
    status: str
    date_submitted: datetime


class SubmissionListItem(ORMModel):
    submission_id: int
    project_id: int
    chapter_no: int
    version: int
    status: str
    note: str | None = None
    has_file: bool
    file_name: str | None = None
    file_size: int | None = None
    date_submitted: datetime


class SubmissionOut(SubmissionListItem):
    content: str | None = None
    mime_type: str | None = None


class CorrectionIn(BaseModel):
    comment: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class CorrectionOut(ORMModel):
    correction_id: int
    submission_id: int
    supervisor_id: int
    supervisor_name: str | None = None
    comment: str
    date_created: datetime


class StatusIn(BaseModel):
    status: Literal["approved", "needs_revision"]
