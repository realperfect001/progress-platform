from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    unauthorized = {"WWW-Authenticate": "Bearer"}
    if creds is None:
        raise AppError(401, "Not authenticated", headers=unauthorized)
    payload = decode_access_token(creds.credentials)
    if not payload:
        raise AppError(401, "Invalid or expired token", headers=unauthorized)
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise AppError(401, "Invalid or expired token", headers=unauthorized)
    user = db.get(User, user_id)
    if user is None:
        raise AppError(401, "Invalid or expired token", headers=unauthorized)
    if not user.is_active:
        raise AppError(403, "Your account has been deactivated")
    if user.role == "supervisor" and not user.is_approved:
        raise AppError(403, "Your account is awaiting approval")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise AppError(403, "You do not have permission to do this")
        return user

    return checker
