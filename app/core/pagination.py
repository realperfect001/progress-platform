from typing import Any

from fastapi import Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import field_error


class PageParams:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def paginate_scalars(db: Session, stmt, params: PageParams) -> dict[str, Any]:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.offset(params.offset).limit(params.page_size)).all()
    return {"items": items, "total": total, "page": params.page, "page_size": params.page_size}


def paginate_list(items: list, params: PageParams) -> dict[str, Any]:
    return {
        "items": items[params.offset : params.offset + params.page_size],
        "total": len(items),
        "page": params.page,
        "page_size": params.page_size,
    }


def apply_sort(stmt, sort: str | None, allowed: dict, default: str):
    key = sort or default
    descending = key.startswith("-")
    column = allowed.get(key.lstrip("-"))
    if column is None:
        raise field_error("sort", f"Sort must be one of: {', '.join(sorted(allowed))}")
    return stmt.order_by(column.desc() if descending else column.asc())


def sort_rows(rows: list[dict], sort: str | None, allowed: set[str], default: str) -> list[dict]:
    key = sort or default
    descending = key.startswith("-")
    name = key.lstrip("-")
    if name not in allowed:
        raise field_error("sort", f"Sort must be one of: {', '.join(sorted(allowed))}")

    def keyfn(row):
        value = row.get(name)
        return (value is None, value if not isinstance(value, str) else value.lower())

    present = sorted((r for r in rows if r.get(name) is not None), key=keyfn, reverse=descending)
    missing = [r for r in rows if r.get(name) is None]
    return present + missing
