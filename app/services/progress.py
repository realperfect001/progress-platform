"""Progress and health, calculated from the latest version of each chapter."""
from collections import defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import utcnow
from app.models.chapter_schedule import ChapterSchedule
from app.models.correction import Correction
from app.models.project import Project
from app.models.submission import Submission


def progress_for_projects(db: Session, projects: list[Project]) -> dict[int, dict[str, Any]]:
    projects = list(projects)
    if not projects:
        return {}
    ids = [p.project_id for p in projects]
    total = settings.TOTAL_CHAPTERS

    submissions = db.scalars(
        select(Submission)
        .where(Submission.project_id.in_(ids))
        .order_by(Submission.project_id, Submission.chapter_no, Submission.version)
    ).all()
    latest: dict[int, dict[int, Submission]] = defaultdict(dict)
    last_activity: dict[int, Any] = {}
    for s in submissions:
        latest[s.project_id][s.chapter_no] = s  # ascending versions: the last one wins
        if s.project_id not in last_activity or s.date_submitted > last_activity[s.project_id]:
            last_activity[s.project_id] = s.date_submitted

    latest_ids = [s.submission_id for chapters in latest.values() for s in chapters.values()]
    corrections: dict[int, tuple[int, Any]] = {}
    if latest_ids:
        rows = db.execute(
            select(
                Correction.submission_id,
                func.count(Correction.correction_id),
                func.max(Correction.date_created),
            )
            .where(Correction.submission_id.in_(latest_ids))
            .group_by(Correction.submission_id)
        ).all()
        corrections = {row[0]: (row[1], row[2]) for row in rows}

    schedule = {row.chapter_no: row.due_date for row in db.scalars(select(ChapterSchedule))}
    now = utcnow()
    today = now.date()

    result: dict[int, dict[str, Any]] = {}
    for project in projects:
        chapter_map = latest.get(project.project_id, {})
        chapters = []
        for n in range(1, total + 1):
            s = chapter_map.get(n)
            if s is None:
                chapters.append(
                    {
                        "chapter_no": n,
                        "status": "not_submitted",
                        "last_updated": None,
                        "corrections_count": 0,
                        "submission_id": None,
                        "version": None,
                        "date_submitted": None,
                    }
                )
                continue
            count, last_correction = corrections.get(s.submission_id, (0, None))
            updated = max(s.date_submitted, last_correction) if last_correction else s.date_submitted
            chapters.append(
                {
                    "chapter_no": n,
                    "status": s.status,
                    "last_updated": updated,
                    "corrections_count": count,
                    "submission_id": s.submission_id,
                    "version": s.version,
                    "date_submitted": s.date_submitted,
                }
            )

        approved = sum(1 for c in chapters if c["status"] == "approved")
        by_no = {c["chapter_no"]: c["status"] for c in chapters}
        if approved == total:
            health = "completed"
        elif schedule:
            overdue = any(
                due < today and by_no.get(n) != "approved"
                for n, due in schedule.items()
                if 1 <= n <= total
            )
            health = "delayed" if overdue else "on_track"
        else:
            reference = last_activity.get(project.project_id) or project.date_created
            health = "delayed" if (now - reference).days >= settings.INACTIVITY_DAYS else "on_track"

        if approved == total:
            status = "completed"
        elif chapter_map:
            status = "in_progress"
        else:
            status = "not_started"

        result[project.project_id] = {
            "percent_complete": round(approved / total * 100, 1),
            "status": status,
            "health": health,
            "chapters": chapters,
            "last_submission_at": last_activity.get(project.project_id),
        }
    return result


def get_progress(db: Session, project: Project) -> dict[str, Any]:
    return progress_for_projects(db, [project])[project.project_id]


def sync_project_status(db: Session, project: Project) -> dict[str, Any]:
    """Stores the derived status on the project. Call db.flush() first so new rows are counted."""
    progress = get_progress(db, project)
    project.status = progress["status"]
    project.updated_at = utcnow()
    return progress
