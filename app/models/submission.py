from datetime import datetime

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, utcnow
from app.models.constants import SUBMISSION_STATUSES


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("project_id", "chapter_no", "version", name="uq_submission_version"),
        CheckConstraint("chapter_no BETWEEN 1 AND 5", name="ck_submission_chapter_no"),
        Index("ix_submissions_project_chapter", "project_id", "chapter_no"),
    )

    submission_id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.project_id", ondelete="CASCADE"))
    chapter_no: Mapped[int]
    version: Mapped[int] = mapped_column(default=1)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(
            *SUBMISSION_STATUSES,
            name="submission_status",
            native_enum=False,
            create_constraint=True,
            length=20,
        ),
        default="submitted",
    )
    date_submitted: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    project = relationship("Project", back_populates="submissions")
    corrections = relationship(
        "Correction", back_populates="submission", cascade="all, delete-orphan"
    )

    @property
    def has_file(self) -> bool:
        return self.file_path is not None
