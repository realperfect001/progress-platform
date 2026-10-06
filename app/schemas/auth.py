import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

from app.schemas.common import ORMModel

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 255 or not _EMAIL_RE.match(value):
        raise ValueError("Enter a valid email address")
    return value


Email = Annotated[str, AfterValidator(_normalize_email)]
Password = Annotated[str, Field(min_length=8, max_length=128)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]


class RegisterIn(BaseModel):
    full_name: Name
    email: Email
    password: Password
    role: Literal["student", "supervisor", "admin"]
    matric_no: Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)] | None = None
    department: Annotated[str, StringConstraints(strip_whitespace=True, max_length=150)] | None = None
    supervisor_id: int | None = None


class LoginIn(BaseModel):
    email: str
    password: str


class ForgotPasswordIn(BaseModel):
    email: str


class ResetPasswordIn(BaseModel):
    token: str
    new_password: Password


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: Password


class ProfileUpdateIn(BaseModel):
    full_name: Name


class SupervisorBrief(ORMModel):
    user_id: int
    full_name: str


class UserOut(ORMModel):
    user_id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    is_approved: bool
    created_at: datetime
    matric_no: str | None = None
    department: str | None = None
    supervisor: SupervisorBrief | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class AccessTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
