from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, field_error
from app.core.security import (
    dummy_hash,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.base import utcnow
from app.models.student import Student
from app.models.tokens import PasswordResetToken, RefreshToken
from app.models.user import User
from app.schemas.auth import RegisterIn


def _blocked_reason(user: User) -> str | None:
    if not user.is_active:
        return "Your account has been deactivated. Contact the administrator."
    if user.role == "supervisor" and not user.is_approved:
        return "Your account is awaiting approval by the administrator."
    return None


def register_user(db: Session, data: RegisterIn) -> User:
    if data.role == "admin":
        raise AppError(403, "Admin accounts cannot be created through registration")
    if db.scalar(select(User.user_id).where(User.email == data.email)):
        raise AppError(409, "An account with this email already exists")

    user = User(
        full_name=data.full_name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        is_active=True,
        is_approved=data.role != "supervisor",
    )
    if data.role == "student":
        if not data.matric_no:
            raise field_error("matric_no", "Matric number is required")
        if not data.department:
            raise field_error("department", "Department is required")
        if data.supervisor_id is None:
            raise field_error("supervisor_id", "Choose a supervisor")
        supervisor = db.get(User, data.supervisor_id)
        if (
            supervisor is None
            or supervisor.role != "supervisor"
            or not supervisor.is_active
            or not supervisor.is_approved
        ):
            raise field_error("supervisor_id", "Choose a valid supervisor")
        matric_no = data.matric_no.upper()
        if db.scalar(select(Student.student_id).where(Student.matric_no == matric_no)):
            raise AppError(409, "A student with this matric number already exists")
        user.student = Student(
            matric_no=matric_no, department=data.department, supervisor_id=supervisor.user_id
        )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "An account with this email or matric number already exists")
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        verify_password(password, dummy_hash())
        raise AppError(401, "Invalid email or password")
    if not verify_password(password, user.password_hash):
        raise AppError(401, "Invalid email or password")
    reason = _blocked_reason(user)
    if reason:
        raise AppError(403, reason)
    return user


def issue_refresh_token(db: Session, user: User) -> str:
    """Adds a hashed refresh token to the transaction and returns the raw value for the cookie."""
    raw = generate_token()
    db.add(
        RefreshToken(
            user_id=user.user_id,
            token_hash=hash_token(raw),
            expires_at=utcnow() + timedelta(days=settings.REFRESH_TOKEN_DAYS),
        )
    )
    return raw


def revoke_user_refresh_tokens(db: Session, user_id: int) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


def rotate_refresh_token(db: Session, raw: str) -> tuple[User, str]:
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    if token is None:
        raise AppError(401, "Invalid or expired session")
    if token.revoked_at is not None:
        # A revoked token being replayed suggests theft: end every session for that user.
        revoke_user_refresh_tokens(db, token.user_id)
        db.commit()
        raise AppError(401, "Invalid or expired session")
    if token.expires_at <= utcnow():
        raise AppError(401, "Invalid or expired session")
    user = db.get(User, token.user_id)
    if user is None or _blocked_reason(user):
        raise AppError(401, "Invalid or expired session")
    token.revoked_at = utcnow()
    new_raw = issue_refresh_token(db, user)
    db.commit()
    return user, new_raw


def revoke_refresh_token(db: Session, raw: str | None) -> None:
    if not raw:
        return
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    if token is not None and token.revoked_at is None:
        token.revoked_at = utcnow()
        db.commit()


def create_reset_token(db: Session, email: str) -> tuple[User, str] | None:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not user.is_active:
        return None
    raw = generate_token()
    db.add(
        PasswordResetToken(
            user_id=user.user_id,
            token_hash=hash_token(raw),
            expires_at=utcnow() + timedelta(minutes=settings.RESET_TOKEN_MINUTES),
        )
    )
    db.commit()
    return user, raw


def reset_password(db: Session, raw: str, new_password: str) -> None:
    token = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(raw))
    )
    if token is None or token.used_at is not None or token.expires_at <= utcnow():
        raise AppError(400, "This reset link is invalid or has expired")
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise AppError(400, "This reset link is invalid or has expired")
    user.password_hash = hash_password(new_password)
    token.used_at = utcnow()
    revoke_user_refresh_tokens(db, user.user_id)
    db.commit()


def change_password(db: Session, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.password_hash):
        raise AppError(400, "Your current password is incorrect")
    user.password_hash = hash_password(new)
    db.commit()


def update_profile(db: Session, user: User, full_name: str) -> User:
    user.full_name = full_name
    db.commit()
    return user
