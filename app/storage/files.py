import re
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import AppError

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
# extension -> (canonical MIME type, required first bytes)
ALLOWED = {
    ".pdf": ("application/pdf", b"%PDF-"),
    ".docx": (DOCX_MIME, b"PK\x03\x04"),
}
# Some browsers/OS combinations send no useful type; the signature check still decides.
GENERIC_MIMES = {"", "application/octet-stream"}
CHUNK = 1024 * 1024


@dataclass
class StoredFile:
    file_name: str  # sanitised display name (never used as a path)
    stored_name: str  # random UUID name on disk, relative to UPLOAD_DIR
    mime_type: str
    size: int


def _clean_name(name: str) -> str:
    name = Path(name.replace("\\", "/")).name
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    if not name:
        return "upload"
    stem, ext = Path(name).stem, Path(name).suffix
    return f"{stem[:200]}{ext}"


def _valid_docx(path: Path) -> bool:
    try:
        if not zipfile.is_zipfile(path):
            return False
        with zipfile.ZipFile(path) as zf:
            return "word/document.xml" in zf.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


def save_upload(upload: UploadFile) -> StoredFile:
    """Validate extension, MIME type, signature and size, then store under a random name."""
    original = _clean_name(upload.filename or "")
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED:
        raise AppError(415, "Only PDF and DOCX files are allowed")
    mime, magic = ALLOWED[ext]
    declared = (upload.content_type or "").split(";")[0].strip().lower()
    if declared != mime and declared not in GENERIC_MIMES:
        raise AppError(415, "The file type does not match its extension")

    root = Path(settings.UPLOAD_DIR)
    root.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest = root / stored_name
    size = 0
    first = True
    try:
        with dest.open("wb") as out:
            while chunk := upload.file.read(CHUNK):
                if first:
                    if not chunk.startswith(magic):
                        raise AppError(415, "The file content does not match its type")
                    first = False
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise AppError(413, f"The file is larger than {settings.MAX_UPLOAD_MB} MB")
                out.write(chunk)
        if size == 0:
            raise AppError(400, "The uploaded file is empty")
        if ext == ".docx" and not _valid_docx(dest):
            raise AppError(415, "The file content does not match its type")
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    return StoredFile(original, stored_name, mime, size)


def resolve_path(stored_name: str) -> Path:
    root = Path(settings.UPLOAD_DIR).resolve()
    path = (root / stored_name).resolve()
    if root not in path.parents or not path.is_file():
        raise AppError(404, "File not found")
    return path


def delete_file(stored_name: str | None) -> None:
    if not stored_name:
        return
    root = Path(settings.UPLOAD_DIR).resolve()
    path = (root / stored_name).resolve()
    if root in path.parents:
        path.unlink(missing_ok=True)
