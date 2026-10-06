FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:////var/data/progress.db
ENV UPLOAD_DIR=/var/data/uploads

WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY start.sh .
RUN chmod +x start.sh

EXPOSE 10000
CMD ["./start.sh"]
