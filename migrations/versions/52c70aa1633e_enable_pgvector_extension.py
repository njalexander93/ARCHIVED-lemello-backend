"""Enable pgvector extension.

Revision ID: 52c70aa1633e
Revises:
Create Date: 2026-02-05 21:34:04.895154

"""

from typing import Sequence, Union

import sqlalchemy as sa  # noqa: F401
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "52c70aa1633e"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Extensions are managed via Alembic so environments stay consistent.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the extension on rollback to keep the migration reversible.
    op.execute("DROP EXTENSION IF EXISTS vector")
