import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger("app")


class AppError(Exception):
    """Business or access error rendered as { detail }."""

    def __init__(
        self,
        status_code: int,
        message: str,
        detail: Any = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.detail = message if detail is None else detail
        self.headers = headers


def field_error(field: str, message: str) -> AppError:
    """422 in FastAPI's validation shape so the front end can map loc to a form field."""
    return AppError(
        422,
        message,
        detail=[{"loc": ["body", field], "msg": message, "type": "value_error"}],
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429, content={"detail": "Too many requests. Please try again shortly."}
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
