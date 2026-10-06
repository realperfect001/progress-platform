from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, utcnow


class Correction(Base):
    __tablename__ = "corrections"

    correction_id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.submission_id", ondelete="CASCADE"), index=True
    )
    supervisor_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    comment: Mapped[str] = mapped_column(Text)
    date_created: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    submission = relationship("Submission", back_populates="corrections")
    supervisor = relationship("User", foreign_keys=[supervisor_id])

    @property
    def supervisor_name(self) -> str | None:
        return self.supervisor.full_name if self.supervisor else None
