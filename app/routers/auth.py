from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Request, Response

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.limiter import limiter
from app.core.errors import AppError
from app.core.security import create_access_token
from app.schemas.auth import (
    AccessTokenOut,
    ForgotPasswordIn,
    LoginIn,
    RegisterIn,
    ResetPasswordIn,
    TokenOut,
    UserOut,
)
from app.schemas.common import Message
from app.services import auth_service
from app.services.email import send_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "refresh_token"
COOKIE_PATH = "/api/v1/auth"


def _cookie_options() -> dict:
    return {
        "httponly": True,
        "secure": settings.is_production,
        "samesite": "none" if settings.is_production else "lax",
        "path": COOKIE_PATH,
    }


def _set_refresh_cookie(response: Response, raw: str) -> None:
    response.set_cookie(
        COOKIE_NAME, raw, max_age=settings.REFRESH_TOKEN_DAYS * 24 * 3600, **_cookie_options()
    )


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: RegisterIn, db: DbSession):
    return auth_service.register_user(db, data)


@router.post("/login", response_model=TokenOut)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def login(request: Request, response: Response, data: LoginIn, db: DbSession):
    user = auth_service.authenticate(db, data.email, data.password)
    raw = auth_service.issue_refresh_token(db, user)
    db.commit()
    _set_refresh_cookie(response, raw)
    return TokenOut(
        access_token=create_access_token(user.user_id, user.role),
        user=UserOut.model_validate(user),
    )


@router.post("/refresh", response_model=AccessTokenOut)
def refresh(
    response: Response,
    db: DbSession,
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    if not refresh_token:
        raise AppError(401, "Not authenticated")
    user, new_raw = auth_service.rotate_refresh_token(db, refresh_token)
    _set_refresh_cookie(response, new_raw)
    return AccessTokenOut(access_token=create_access_token(user.user_id, user.role))


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    db: DbSession,
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    auth_service.revoke_refresh_token(db, refresh_token)
    response.delete_cookie(COOKIE_NAME, **_cookie_options())


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.post("/forgot-password", response_model=Message)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def forgot_password(
    request: Request, data: ForgotPasswordIn, background: BackgroundTasks, db: DbSession
):
    result = auth_service.create_reset_token(db, data.email)
    if result is not None:
        user, raw = result
        background.add_task(send_reset_email, user.email, raw)
    return Message(detail="If that email is registered, a reset link has been sent.")


@router.post("/reset-password", response_model=Message)
def reset_password(data: ResetPasswordIn, db: DbSession):
    auth_service.reset_password(db, data.token, data.new_password)
    return Message(detail="Your password has been updated.")
