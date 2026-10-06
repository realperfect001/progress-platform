from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.user import User
from app.schemas.auth import ChangePasswordIn, ProfileUpdateIn, SupervisorBrief, UserOut
from app.services import auth_service

router = APIRouter(tags=["users"])


@router.patch("/users/me", response_model=UserOut)
def update_me(data: ProfileUpdateIn, user: CurrentUser, db: DbSession):
    return auth_service.update_profile(db, user, data.full_name)


@router.post("/users/me/change-password", status_code=204)
def change_password(data: ChangePasswordIn, user: CurrentUser, db: DbSession):
    auth_service.change_password(db, user, data.current_password, data.new_password)


@router.get("/supervisors", response_model=list[SupervisorBrief])
def list_supervisors(db: DbSession):
    """Public (used by the registration form): approved, active supervisors; names only."""
    stmt = (
        select(User)
        .where(User.role == "supervisor", User.is_active.is_(True), User.is_approved.is_(True))
        .order_by(User.full_name)
    )
    return list(db.scalars(stmt))
