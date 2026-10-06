from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

from app.schemas.auth import SupervisorBrief
from app.schemas.common import ORMModel

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=255)]
Health = Literal["on_track", "delayed", "completed"]


class ProjectIn(BaseModel):
    title: Title


class ProjectOut(ORMModel):
    project_id: int
    student_id: int
    title: str
    status: str
    date_created: datetime
    updated_at: datetime


class ChapterProgress(ORMModel):
    chapter_no: int
    status: str  # not_submitted | submitted | under_review | needs_revision | approved
    last_updated: datetime | None = None
    corrections_count: int = 0
    submission_id: int | None = None
    version: int | None = None


class ProgressOut(BaseModel):
    percent_complete: float
    status: Literal["not_started", "in_progress", "completed"]
    health: Health
    chapters: list[ChapterProgress]


class SupervisorStudentItem(BaseModel):
    student_id: int
    full_name: str
    matric_no: str
    project_id: int | None = None
    title: str | None = None
    percent_complete: float = 0
    health: Health | None = None
    last_submission_at: datetime | None = None


class AdminProjectItem(BaseModel):
    project_id: int
    title: str
    status: str
    health: Health
    percent_complete: float
    student_id: int
    student_name: str
    matric_no: str
    supervisor_id: int | None = None
    supervisor_name: str | None = None
    date_created: datetime
    updated_at: datetime
    last_submission_at: datetime | None = None


class StudentProject(ProjectOut):
    percent_complete: float
    health: Health


class StudentDetail(BaseModel):
    student_id: int
    full_name: str
    email: str
    matric_no: str
    department: str
    supervisor: SupervisorBrief | None = None
    project: StudentProject | None = None
