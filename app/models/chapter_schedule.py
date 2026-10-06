from datetime import date

from sqlalchemy import Date
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChapterSchedule(Base):
    __tablename__ = "chapter_schedule"

    chapter_no: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    due_date: Mapped[date] = mapped_column(Date)
