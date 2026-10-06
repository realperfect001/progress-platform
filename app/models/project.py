from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, utcnow
from app.models.constants import PROJECT_STATUSES


class Project(Base):
    __tablename__ = "projects"

    project_id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"), unique=True
    )
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        Enum(
            *PROJECT_STATUSES,
            name="project_status",
            native_enum=False,
            create_constraint=True,
            length=20,
        ),
        default="not_started",
    )
    date_created: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    student = relationship("Student", back_populates="project")
    submissions = relationship(
        "Submission", back_populates="project", cascade="all, delete-orphan"
    )
