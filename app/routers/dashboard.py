from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import DbSession, require_role
from app.models.user import User
from app.schemas.dashboards import AdminDashboard, StudentDashboard, SupervisorDashboard
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/student", response_model=StudentDashboard)
def student(user: Annotated[User, Depends(require_role("student"))], db: DbSession):
    return dashboard_service.student_dashboard(db, user)


@router.get("/supervisor", response_model=SupervisorDashboard)
def supervisor(user: Annotated[User, Depends(require_role("supervisor"))], db: DbSession):
    return dashboard_service.supervisor_dashboard(db, user)


@router.get("/admin", response_model=AdminDashboard)
def admin(_admin: Annotated[User, Depends(require_role("admin"))], db: DbSession):
    return dashboard_service.admin_dashboard(db)
