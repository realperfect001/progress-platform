from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class NotificationOut(ORMModel):
    notification_id: int
    message: str
    type: str
    related_type: str | None = None
    related_id: int | None = None
    is_read: bool
    date_created: datetime


class UnreadCount(BaseModel):
    count: int
