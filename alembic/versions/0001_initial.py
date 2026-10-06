"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-06

The first revision builds the schema from the models as they are today. Every later change
should be a normal migration:  alembic revision --autogenerate -m "describe the change"
"""
from alembic import op

import app.models  # noqa: F401
from app.db.base import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
