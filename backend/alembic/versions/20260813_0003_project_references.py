"""Add user-managed project references."""

from alembic import op
import sqlalchemy as sa


revision = "20260813_0003"
down_revision = "20260813_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_references",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("authors", sa.String(length=512)),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("source", sa.String(length=512)),
        sa.Column("year", sa.String(length=32)),
        sa.Column("extra", sa.Text()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("project_references")
