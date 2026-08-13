"""Add users and bind existing projects to admin."""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "20260813_0004"
down_revision = "20260813_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    now = datetime.now(timezone.utc)
    op.bulk_insert(
        sa.table(
            "users",
            sa.column("id", sa.String),
            sa.column("username", sa.String),
            sa.column("password_hash", sa.String),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "id": "admin",
                "username": "admin",
                "password_hash": (
                    "pbkdf2_sha256$210000$"
                    "YWRtaW4tZGVmYXVsdC1zYWx0$"
                    "WLf7XaH2kzrAe9Lx5M+NPv7Mh+xcgcK+wVZB03MmMkE="
                ),
                "created_at": now,
                "updated_at": now,
            }
        ],
    )
    op.execute("UPDATE projects SET user_id = 'admin'")


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
