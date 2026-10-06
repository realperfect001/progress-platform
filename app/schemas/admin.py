from datetime import date

from pydantic import BaseModel, model_validator


class ScheduleItem(BaseModel):
    chapter_no: int
    due_date: date


class ScheduleIn(BaseModel):
    chapters: list[ScheduleItem]


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    is_approved: bool | None = None

    @model_validator(mode="after")
    def _at_least_one(self):
        if self.is_active is None and self.is_approved is None:
            raise ValueError("Send is_active and/or is_approved")
        return self


class AssignSupervisorIn(BaseModel):
    supervisor_id: int
