from datetime import datetime

from pydantic import BaseModel

from app.schemas.notifications import NotificationOut
from app.schemas.projects import (
    AdminProjectItem,
    ChapterProgress,
    Health,
    ProjectOut,
    SupervisorStudentItem,
)


class StudentDashboard(BaseModel):
    project: ProjectOut | None = None
    percent_complete: float
    health: Health | None = None
    chapters: list[ChapterProgress]
    needs_attention: list[ChapterProgress]
    recent_notifications: list[NotificationOut]


class SupervisorCounts(BaseModel):
    students: int
    awaiting_review: int
    needs_revision: int
    delayed: int


class ReviewQueueItem(BaseModel):
    submission_id: int
    project_id: int
    student_id: int
    student_name: str
    matric_no: str
    chapter_no: int
    version: int | None = None
    status: str
    date_submitted: datetime | None = None


class ActivityItem(BaseModel):
    type: str
    message: str
    related_type: str
    related_id: int
    date: datetime


class SupervisorDashboard(BaseModel):
    counts: SupervisorCounts
    review_queue: list[ReviewQueueItem]
    at_risk: list[SupervisorStudentItem]
    recent_activity: list[ActivityItem]


class AdminTotals(BaseModel):
    students: int
    supervisors: int
    projects: int


class SupervisorProgress(BaseModel):
    supervisor_id: int
    full_name: str
    students: int
    average_percent: float
    delayed: int


class AdminDashboard(BaseModel):
    totals: AdminTotals
    progress_by_supervisor: list[SupervisorProgress]
    delayed_projects: list[AdminProjectItem]
