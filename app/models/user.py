from datetime import datetime

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, utcnow
from app.models.constants import ROLES


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(
        Enum(*ROLES, name="user_role", native_enum=False, create_constraint=True, length=20)
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    is_approved: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    student = relationship(
        "Student", foreign_keys="Student.student_id", back_populates="user", uselist=False
    )

    @property
    def matric_no(self) -> str | None:
        return self.student.matric_no if self.student else None

    @property
    def department(self) -> str | None:
        return self.student.department if self.student else None

    @property
    def supervisor(self):
        return self.student.supervisor if self.student else None
