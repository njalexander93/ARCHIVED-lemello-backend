"""create_users_table.

Revision ID: 85729e3285a2
Revises: 52c70aa1633e
Create Date: 2026-03-05 00:54:04.167216

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "85729e3285a2"
down_revision: Union[str, Sequence[str], None] = "52c70aa1633e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=30), nullable=False),
        sa.Column("hashed_password", sa.String(length=128), nullable=True),
        sa.Column(
            "password_changed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "email_verified_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "role",
            sa.String(length=20),
            server_default=sa.text("'user'"),
            nullable=False,
        ),
        sa.Column(
            "preferences",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()),
                "postgresql",
            ),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(
        "ix_users_email_lower",
        "users",
        [sa.text("LOWER(email)")],
        unique=True,
    )
    op.create_index(
        "ix_users_username_lower",
        "users",
        [sa.text("LOWER(username)")],
        unique=True,
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER set_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS set_updated_at ON users")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    op.drop_index("ix_users_username_lower", table_name="users")
    op.drop_index("ix_users_email_lower", table_name="users")
    op.drop_table("users")
