from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, require_role
from app.core.pagination import PageParams
from app.models.user import User
from app.schemas.admin import AdminUserUpdate, AssignSupervisorIn, ScheduleIn, ScheduleItem
from app.schemas.auth import UserOut
from app.schemas.common import Page
from app.schemas.projects import StudentDetail
from app.services import admin_service

router = APIRouter(tags=["admin"])

AdminUser = Annotated[User, Depends(require_role("admin"))]


@router.get("/admin/users", response_model=Page[UserOut])
def list_users(
    _admin: AdminUser,
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    role: str | None = None,
    search: str | None = None,
    sort: str | None = None,
):
    return admin_service.list_users(db, role, search, params, sort)


@router.patch("/admin/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: AdminUserUpdate, admin: AdminUser, db: DbSession):
    return admin_service.update_user(db, admin, user_id, data.is_active, data.is_approved)


@router.patch("/admin/students/{student_id}/supervisor", response_model=StudentDetail)
def assign_supervisor(student_id: int, data: AssignSupervisorIn, _admin: AdminUser, db: DbSession):
    return admin_service.assign_supervisor(db, student_id, data.supervisor_id)


@router.get("/chapter-schedule", response_model=list[ScheduleItem])
def get_schedule(_user: CurrentUser, db: DbSession):
    return admin_service.get_schedule(db)


@router.put("/admin/chapter-schedule", response_model=list[ScheduleItem])
def put_schedule(data: ScheduleIn, _admin: AdminUser, db: DbSession):
    return admin_service.replace_schedule(db, data.chapters)
