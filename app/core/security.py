import hashlib
import secrets
from datetime import timedelta
from functools import lru_cache

import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.db.base import utcnow

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=settings.BCRYPT_ROUNDS)


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _pwd.verify(password, password_hash)
    except ValueError:
        return False


@lru_cache
def dummy_hash() -> str:
    """Used to spend the same time on unknown emails as on known ones."""
    return _pwd.hash("not-a-real-password")


def create_access_token(user_id: int, role: str) -> str:
    exp = utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    payload = {"sub": str(user_id), "role": role, "exp": exp}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def generate_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
