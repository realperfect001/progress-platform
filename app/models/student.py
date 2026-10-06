from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Student(Base):
    __tablename__ = "students"

    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True, autoincrement=False
    )
    matric_no: Mapped[str] = mapped_column(String(50), unique=True)
    department: Mapped[str] = mapped_column(String(150))
    supervisor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id"), nullable=True, index=True
    )

    user = relationship("User", foreign_keys=[student_id], back_populates="student")
    supervisor = relationship("User", foreign_keys=[supervisor_id])
    project = relationship("Project", back_populates="student", uselist=False)
