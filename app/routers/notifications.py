from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession
from app.core.pagination import PageParams
from app.schemas.common import Page
from app.schemas.notifications import NotificationOut, UnreadCount
from app.services import notifications as service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Page[NotificationOut])
def list_notifications(
    user: CurrentUser,
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    unread: bool = False,
):
    return service.list_notifications(db, user, params, unread)


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(user: CurrentUser, db: DbSession):
    return UnreadCount(count=service.unread_count(db, user))


@router.post("/read-all", status_code=204)
def read_all(user: CurrentUser, db: DbSession):
    service.mark_all_read(db, user)


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, user: CurrentUser, db: DbSession):
    return service.mark_read(db, user, notification_id)
