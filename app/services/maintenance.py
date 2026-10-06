import asyncio
import logging
import sqlite3
from datetime import datetime, timezone

from sqlalchemy import delete, or_
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.db.base import utcnow
from app.db.session import SessionLocal
from app.models.tokens import PasswordResetToken, RefreshToken

logger = logging.getLogger("app.maintenance")


def backup_database() -> None:
    """Copies the database with SQLite's backup API (safe while the API is writing)."""
    url = make_url(settings.DATABASE_URL)
    if not url.drivername.startswith("sqlite") or not url.database:
        return
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = settings.backup_dir / f"progress-{stamp}.db"
    source = sqlite3.connect(url.database)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    backups = sorted(settings.backup_dir.glob("progress-*.db"))
    for old in backups[: -settings.BACKUP_KEEP]:
        old.unlink(missing_ok=True)
    logger.info("Database backup written to %s", target)


def purge_expired_tokens() -> None:
    with SessionLocal() as db:
        now = utcnow()
        db.execute(
            delete(RefreshToken).where(
                or_(RefreshToken.expires_at < now, RefreshToken.revoked_at.is_not(None))
            )
        )
        db.execute(
            delete(PasswordResetToken).where(
                or_(PasswordResetToken.expires_at < now, PasswordResetToken.used_at.is_not(None))
            )
        )
        db.commit()


def run_daily_tasks() -> None:
    for task in (backup_database, purge_expired_tokens):
        try:
            task()
        except Exception:
            logger.exception("Maintenance task %s failed", task.__name__)


async def maintenance_loop() -> None:
    await asyncio.sleep(60)  # let the service finish starting
    while True:
        await asyncio.to_thread(run_daily_tasks)
        await asyncio.sleep(24 * 60 * 60)
