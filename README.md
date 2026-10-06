# Project Progress Platform API

FastAPI + SQLite backend for the Department of Computer Science, Moshood Abiola Polytechnic.
Implements the *Backend Implementation Document*: roles, projects, versioned chapter submissions,
the correction cycle, progress/health, notifications, dashboards, admin tools, Docker and Render.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
# edit .env for a local run:
#   DATABASE_URL=sqlite:///./progress.db   UPLOAD_DIR=./uploads   ENV=development
#   FRONTEND_ORIGIN=http://localhost:5173
alembic upgrade head
uvicorn app.main:app --reload
```

Swagger: http://localhost:8000/docs  ·  Health: `GET /health`  ·  API base: `/api/v1`

Create the first admin (admins cannot self-register):

```bash
python -m app.create_admin "Admin Name" admin@poly.edu.ng "a-strong-password"
```

## Tests

```bash
pytest -q
```

Uses a temporary SQLite file with the same PRAGMAs as production (`foreign_keys`, WAL, busy timeout).

## Docker

```bash
docker build -t progress-platform-api .
docker run --rm -p 8000:10000 --env-file .env -v progress-data:/var/data progress-platform-api
# or: docker compose up --build
```

`start.sh` must keep **LF** line endings. For Docker on your own computer set `ENV=development`
in `.env` (a `Secure` cookie is not sent over plain http).

## Deploy on Render

Follow Section 10 of the document: Docker web service, **paid** instance, **one** instance,
Disk `progress-data` mounted at `/var/data`, health check `/health`, then set `SECRET_KEY`,
`FRONTEND_ORIGIN` (exact https URL, no trailing slash) and `ENV=production`.
`render.yaml` recreates the same service. Then set the front end's `VITE_API_BASE_URL`
to `https://<service>.onrender.com/api/v1`.

## Layout

```
app/main.py        app, CORS, routers, health, size guard
app/core/          config, security (bcrypt/JWT), deps (auth + roles), errors, pagination, limiter
app/db/            base (UTC datetime type), session (engine + SQLite PRAGMAs)
app/models/        users, students, projects, submissions, corrections, notifications, tokens, chapter_schedule
app/schemas/       Pydantic request/response models (response_model on every route)
app/routers/       thin HTTP layer
app/services/      all business rules (access, submissions, corrections, progress, notifications, ...)
app/storage/       upload validation and safe file access
alembic/           migrations (batch mode)
tests/             pytest suite
```

## Choices where the document left room

- **Chapter progress payload** lists all 5 chapters; an unsubmitted chapter has `status: "not_submitted"`.
  Each entry also carries `submission_id` and `version` so the UI can link to the latest version.
  `corrections_count` is for the latest version of the chapter.
- **Opening a submission** as its assigned supervisor (detail or file download) moves
  `submitted` -> `under_review`. Adding the first correction does the same.
- **Decided versions are final**: only `submitted`/`under_review` can become `approved` or
  `needs_revision`; anything else is 409.
- **Registering as admin** returns 403. Invalid `supervisor_id` returns 422 with `loc: ["body","supervisor_id"]`.
- **Uploads**: extension, MIME type, signature and size are checked. A generic MIME
  (`application/octet-stream` or empty) is accepted because some systems send it for `.docx`;
  the file signature (and `word/document.xml` for DOCX) still decides.
- **Chapter schedule**: `PUT /admin/chapter-schedule` replaces the whole schedule; chapters left out lose their deadline.
  With no schedule rows, health falls back to `INACTIVITY_DAYS`.
- **Extras**: `sort` on list endpoints, a request-size guard (413), a daily in-process task that backs up the
  database (SQLite backup API, keeps `BACKUP_KEEP`) and purges expired tokens, replay of a revoked refresh token ends all of that user's sessions.
- **First migration** builds the tables from the models. Later changes: `alembic revision --autogenerate -m "..."`.
