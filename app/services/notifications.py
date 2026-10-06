from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.pagination import PageParams, paginate_scalars
from app.models.notification import Notification
from app.models.user import User


def notify(
    db: Session,
    user_id: int,
    message: str,
    type_: str,
    related_type: str | None = None,
    related_id: int | None = None,
) -> Notification:
    """Adds a row to the caller's transaction. The caller commits."""
    notification = Notification(
        user_id=user_id,
        message=message,
        type=type_,
        related_type=related_type,
        related_id=related_id,
    )
    db.add(notification)
    return notification


def list_notifications(db: Session, user: User, params: PageParams, unread_only: bool):
    stmt = select(Notification).where(Notification.user_id == user.user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.date_created.desc(), Notification.notification_id.desc())
    return paginate_scalars(db, stmt, params)


def recent_notifications(db: Session, user: User, limit: int = 5) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user.user_id)
        .order_by(Notification.date_created.desc(), Notification.notification_id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def unread_count(db: Session, user: User) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user.user_id, Notification.is_read.is_(False))
        )
        or 0
    )


def mark_read(db: Session, user: User, notification_id: int) -> Notification:
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.user_id:
        raise AppError(404, "Notification not found")
    notification.is_read = True
    db.commit()
    return notification


def mark_all_read(db: Session, user: User) -> None:
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    db.commit()
