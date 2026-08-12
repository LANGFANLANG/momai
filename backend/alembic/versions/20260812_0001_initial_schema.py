"""Create the initial paper-agent schema."""

from alembic import op
import sqlalchemy as sa


revision = "20260812_0001"
down_revision = None
branch_labels = None
depends_on = None


def id_column() -> sa.Column:
    return sa.Column("id", sa.String(length=36), primary_key=True)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    project_type = sa.Enum("course_report", "thesis", "proposal", name="project_type")
    project_status = sa.Enum(
        "drafting_info", "brief_ready", "outline_ready", "relations_ready",
        "drafting_chapters", "review_ready", "export_ready", name="project_status",
    )
    chapter_status = sa.Enum("planned", "relation_ready", "drafting", "drafted", "reviewed", name="chapter_status")
    draft_mode = sa.Enum("generate", "rewrite", "continue", "expand", "compress", "polish", name="draft_mode")
    material_type = sa.Enum(
        "requirement", "code_summary", "database_schema", "experiment_data", "reference",
        "advisor_feedback", "template", "other", name="material_type",
    )
    feedback_status = sa.Enum("open", "applied", "ignored", name="feedback_status")
    issue_severity = sa.Enum("low", "medium", "high", name="issue_severity")
    issue_status = sa.Enum("open", "fixed", "ignored", name="issue_status")
    export_format = sa.Enum("markdown", "docx", "pdf", "latex", name="export_format")

    op.create_table(
        "projects",
        id_column(),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("type", project_type, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("major", sa.String(length=255)),
        sa.Column("school", sa.String(length=255)),
        sa.Column("target_word_count", sa.Integer()),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("requirements", sa.Text()),
        sa.Column("status", project_status, nullable=False),
        *timestamps(),
    )
    op.create_table(
        "project_contexts",
        id_column(),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("background", sa.Text()), sa.Column("problem", sa.Text()), sa.Column("goal", sa.Text()),
        sa.Column("scenario", sa.Text()), sa.Column("target_users", sa.Text()), sa.Column("methods", sa.JSON()),
        sa.Column("technologies", sa.JSON()), sa.Column("modules", sa.JSON()), sa.Column("architecture", sa.Text()),
        sa.Column("environment", sa.Text()), sa.Column("data_sources", sa.JSON()), sa.Column("experiments", sa.Text()),
        sa.Column("innovations", sa.JSON()), sa.Column("constraints", sa.JSON()), sa.Column("writing_prefs", sa.JSON()),
        *timestamps(),
    )
    op.create_table(
        "project_briefs",
        id_column(),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("title_explanation", sa.Text()), sa.Column("background", sa.Text()), sa.Column("core_problem", sa.Text()),
        sa.Column("goal", sa.Text()), sa.Column("significance", sa.Text()), sa.Column("technical_route", sa.Text()),
        sa.Column("modules", sa.JSON()), sa.Column("expected_result", sa.Text()), sa.Column("writing_boundary", sa.Text()),
        sa.Column("missing_info", sa.JSON()), sa.Column("locked_facts", sa.JSON()), *timestamps(),
    )
    op.create_table(
        "chapters",
        id_column(),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", sa.String(length=36), sa.ForeignKey("chapters.id", ondelete="CASCADE")),
        sa.Column("title", sa.String(length=255), nullable=False), sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False), sa.Column("purpose", sa.Text()),
        sa.Column("suggested_word_count", sa.Integer()), sa.Column("status", chapter_status, nullable=False), *timestamps(),
    )
    op.create_table(
        "chapter_relations",
        id_column(),
        sa.Column("chapter_id", sa.String(length=36), sa.ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("previous_bridge", sa.Text()), sa.Column("next_bridge", sa.Text()),
        sa.Column("required_questions", sa.JSON()), sa.Column("depends_on_facts", sa.JSON()),
        sa.Column("key_points", sa.JSON()), sa.Column("output_conclusions", sa.JSON()), sa.Column("avoid_repeating", sa.JSON()),
        *timestamps(),
    )
    op.create_table(
        "chapter_drafts",
        id_column(),
        sa.Column("chapter_id", sa.String(length=36), sa.ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False), sa.Column("content", sa.Text(), nullable=False),
        sa.Column("prompt_snapshot", sa.JSON()), sa.Column("generation_mode", draft_mode, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "chapter_summaries",
        id_column(),
        sa.Column("chapter_id", sa.String(length=36), sa.ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False), sa.Column("key_conclusions", sa.JSON()),
        sa.Column("used_facts", sa.JSON()), sa.Column("forward_implications", sa.JSON()), *timestamps(),
    )
    op.create_table(
        "materials",
        id_column(),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", material_type, nullable=False), sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text()), sa.Column("file_url", sa.String(length=2048)), sa.Column("metadata", sa.JSON()), *timestamps(),
    )
    op.create_table(
        "feedback_items",
        id_column(),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chapter_id", sa.String(length=36), sa.ForeignKey("chapters.id", ondelete="SET NULL")),
        sa.Column("raw_text", sa.Text(), nullable=False), sa.Column("category", sa.String(length=255)),
        sa.Column("status", feedback_status, nullable=False), sa.Column("suggestion", sa.Text()), *timestamps(),
    )
    op.create_table(
        "consistency_issues",
        id_column(),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chapter_id", sa.String(length=36), sa.ForeignKey("chapters.id", ondelete="SET NULL")),
        sa.Column("severity", issue_severity, nullable=False), sa.Column("type", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False), sa.Column("suggestion", sa.Text()),
        sa.Column("status", issue_status, nullable=False), *timestamps(),
    )
    op.create_table(
        "export_records",
        id_column(),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", export_format, nullable=False), sa.Column("file_url", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in (
        "export_records", "consistency_issues", "feedback_items", "materials", "chapter_summaries",
        "chapter_drafts", "chapter_relations", "chapters", "project_briefs", "project_contexts", "projects",
    ):
        op.drop_table(table)

    for enum_name in (
        "export_format", "issue_status", "issue_severity", "feedback_status", "material_type",
        "draft_mode", "chapter_status", "project_status", "project_type",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
