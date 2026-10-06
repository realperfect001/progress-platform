"""Ownership rules. Anything outside the user's reach is reported as 404, never 403."""
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.project import Project
from app.models.submission import Submission
from app.models.user import User


def can_access_project(user: User, project: Project) -> bool:
    if user.role == "admin":
        return True
    if user.role == "student":
        return project.student_id == user.user_id
    if user.role == "supervisor":
        return project.student.supervisor_id == user.user_id
    return False


def get_project_or_404(db: Session, user: User, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None or not can_access_project(user, project):
        raise AppError(404, "Project not found")
    return project


def get_submission_or_404(db: Session, user: User, submission_id: int) -> Submission:
    submission = db.get(Submission, submission_id)
    if submission is None or not can_access_project(user, submission.project):
        raise AppError(404, "Submission not found")
    return submission
