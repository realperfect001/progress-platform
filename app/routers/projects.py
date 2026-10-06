from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, require_role
from app.core.pagination import PageParams
from app.models.user import User
from app.schemas.common import Page
from app.schemas.projects import (
    AdminProjectItem,
    Health,
    ProgressOut,
    ProjectIn,
    ProjectOut,
    StudentDetail,
    SupervisorStudentItem,
)
from app.services import project_service
from app.services.access import get_project_or_404
from app.services.progress import get_progress

router = APIRouter(tags=["projects"])

StudentUser = Annotated[User, Depends(require_role("student"))]
SupervisorUser = Annotated[User, Depends(require_role("supervisor"))]
AdminUser = Annotated[User, Depends(require_role("admin"))]
StaffUser = Annotated[User, Depends(require_role("supervisor", "admin"))]


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(data: ProjectIn, user: StudentUser, db: DbSession):
    return project_service.create_project(db, user, data.title)


@router.get("/projects/me", response_model=ProjectOut)
def my_project(user: StudentUser, db: DbSession):
    return project_service.get_my_project(db, user)


@router.get("/projects", response_model=Page[AdminProjectItem])
def list_projects(
    _admin: AdminUser,
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    supervisor_id: int | None = None,
    status: str | None = None,
    health: Health | None = None,
    search: str | None = None,
    sort: str | None = None,
):
    return project_service.admin_projects(db, supervisor_id, status, health, search, params, sort)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, data: ProjectIn, user: StudentUser, db: DbSession):
    return project_service.update_project(db, user, project_id, data.title)


@router.get("/projects/{project_id}/progress", response_model=ProgressOut)
def project_progress(project_id: int, user: CurrentUser, db: DbSession):
    project = get_project_or_404(db, user, project_id)
    return get_progress(db, project)


@router.get("/supervisor/students", response_model=Page[SupervisorStudentItem])
def supervisor_students(
    user: SupervisorUser,
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    search: str | None = None,
    health: Health | None = None,
    sort: str | None = None,
):
    return project_service.supervisor_students(db, user, search, health, params, sort)


@router.get("/students/{student_id}", response_model=StudentDetail)
def student_detail(student_id: int, user: StaffUser, db: DbSession):
    return project_service.get_student_detail(db, user, student_id)
