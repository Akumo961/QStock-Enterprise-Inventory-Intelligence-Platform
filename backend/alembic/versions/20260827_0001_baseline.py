"""QStock initial database schema baseline.

Revision ID: 20260827_0001
Revises:
Create Date: 2026-08-27

This baseline captures the schema represented by the SQLAlchemy models at the
start of Phase 10. It is intentionally model-driven so a fresh production
PostgreSQL database can be initialized through Alembic instead of relying on
application startup DDL.
"""

from typing import Sequence, Union

from alembic import op

from src.core.database import Base
from src import models  # noqa: F401 - register all ORM models

revision: str = "20260827_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
