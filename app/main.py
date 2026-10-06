import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.deps import DbSession
from app.core.errors import register_error_handlers
from app.core.limiter import limiter
from app.routers import admin, auth, dashboard, notifications, projects, submissions, users
from app.services.maintenance import maintenance_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(maintenance_loop()) if settings.MAINTENANCE_ENABLED else None
    try:
        yield
    finally:
        if task:
            task.cancel()


app = FastAPI(
    title="Project Progress Platform API",
    version="1.0.0",
    description="Backend for the Department of Computer Science, Moshood Abiola Polytechnic.",
    lifespan=lifespan,
)
app.state.limiter = limiter
register_error_handlers(app)

@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Refuse oversized bodies early (the file check in storage/files.py is the exact one)."""
    length = request.headers.get("content-length")
    limit = settings.max_upload_bytes + 1024 * 1024  # room for form fields and multipart overhead
    if length and length.isdigit() and int(length) > limit:
        return JSONResponse(
            status_code=413,
            content={"detail": f"The request is larger than {settings.MAX_UPLOAD_MB} MB"},
        )
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


for module in (auth, users, projects, submissions, dashboard, notifications, admin):
    app.include_router(module.router, prefix=API_PREFIX)


@app.get("/health", tags=["health"])
def health(db: DbSession):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Database unavailable"})
    return {"status": "ok"}
