"""Add paper abstracts for bilingual front matter."""

from alembic import op
import sqlalchemy as sa


revision = "20260813_0002"
down_revision = "20260812_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_abstracts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("title_en", sa.String(length=512)),
        sa.Column("abstract_zh", sa.Text()),
        sa.Column("abstract_en", sa.Text()),
        sa.Column("keywords_zh", sa.JSON()),
        sa.Column("keywords_en", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("paper_abstracts")
