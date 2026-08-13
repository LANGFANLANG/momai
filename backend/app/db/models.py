from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

PROJECT_TYPES = ("course_report", "thesis", "proposal")
PROJECT_STATUSES = (
    "drafting_info",
    "brief_ready",
    "outline_ready",
    "relations_ready",
    "drafting_chapters",
    "review_ready",
    "export_ready",
)
CHAPTER_STATUSES = ("planned", "relation_ready", "drafting", "drafted", "reviewed")
DRAFT_MODES = ("generate", "rewrite", "continue", "expand", "compress", "polish")
MATERIAL_TYPES = (
    "requirement",
    "code_summary",
    "database_schema",
    "experiment_data",
    "reference",
    "advisor_feedback",
    "template",
    "other",
)
FEEDBACK_STATUSES = ("open", "applied", "ignored")
ISSUE_SEVERITIES = ("low", "medium", "high")
ISSUE_STATUSES = ("open", "fixed", "ignored")
EXPORT_FORMATS = ("markdown", "docx", "pdf", "latex")


def uuid_string() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    projects: Mapped[list["Project"]] = relationship(back_populates="user")


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), default="admin")
    type: Mapped[str] = mapped_column(Enum(*PROJECT_TYPES, name="project_type"))
    title: Mapped[str] = mapped_column(String(255))
    major: Mapped[str | None] = mapped_column(String(255))
    school: Mapped[str | None] = mapped_column(String(255))
    target_word_count: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(String(32))
    requirements: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Enum(*PROJECT_STATUSES, name="project_status"), default="drafting_info"
    )

    context: Mapped["ProjectContext | None"] = relationship(
        back_populates="project", cascade="all, delete-orphan", uselist=False
    )
    brief: Mapped["ProjectBrief | None"] = relationship(
        back_populates="project", cascade="all, delete-orphan", uselist=False
    )
    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    materials: Mapped[list["Material"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    feedback_items: Mapped[list["FeedbackItem"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    consistency_issues: Mapped[list["ConsistencyIssue"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    export_records: Mapped[list["ExportRecord"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    paper_abstract: Mapped["PaperAbstract | None"] = relationship(
        back_populates="project", cascade="all, delete-orphan", uselist=False
    )
    references: Mapped[list["ProjectReference"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectReference.sort_order",
    )
    user: Mapped[User] = relationship(back_populates="projects")


class ProjectContext(TimestampMixin, Base):
    __tablename__ = "project_contexts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    background: Mapped[str | None] = mapped_column(Text)
    problem: Mapped[str | None] = mapped_column(Text)
    goal: Mapped[str | None] = mapped_column(Text)
    scenario: Mapped[str | None] = mapped_column(Text)
    target_users: Mapped[str | None] = mapped_column(Text)
    methods: Mapped[list[str] | None] = mapped_column(JSON)
    technologies: Mapped[list[str] | None] = mapped_column(JSON)
    modules: Mapped[list[str] | None] = mapped_column(JSON)
    architecture: Mapped[str | None] = mapped_column(Text)
    environment: Mapped[str | None] = mapped_column(Text)
    data_sources: Mapped[list[str] | None] = mapped_column(JSON)
    experiments: Mapped[str | None] = mapped_column(Text)
    innovations: Mapped[list[str] | None] = mapped_column(JSON)
    constraints: Mapped[list[str] | None] = mapped_column(JSON)
    writing_prefs: Mapped[dict | None] = mapped_column(JSON)

    project: Mapped[Project] = relationship(back_populates="context")


class ProjectBrief(TimestampMixin, Base):
    __tablename__ = "project_briefs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    title_explanation: Mapped[str | None] = mapped_column(Text)
    background: Mapped[str | None] = mapped_column(Text)
    core_problem: Mapped[str | None] = mapped_column(Text)
    goal: Mapped[str | None] = mapped_column(Text)
    significance: Mapped[str | None] = mapped_column(Text)
    technical_route: Mapped[str | None] = mapped_column(Text)
    modules: Mapped[list[str] | None] = mapped_column(JSON)
    expected_result: Mapped[str | None] = mapped_column(Text)
    writing_boundary: Mapped[str | None] = mapped_column(Text)
    missing_info: Mapped[list[str] | None] = mapped_column(JSON)
    locked_facts: Mapped[list[str] | None] = mapped_column(JSON)

    project: Mapped[Project] = relationship(back_populates="brief")


class PaperAbstract(TimestampMixin, Base):
    __tablename__ = "paper_abstracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    title_en: Mapped[str | None] = mapped_column(String(512))
    abstract_zh: Mapped[str | None] = mapped_column(Text)
    abstract_en: Mapped[str | None] = mapped_column(Text)
    keywords_zh: Mapped[list[str] | None] = mapped_column(JSON)
    keywords_en: Mapped[list[str] | None] = mapped_column(JSON)

    project: Mapped[Project] = relationship(back_populates="paper_abstract")


class ProjectReference(TimestampMixin, Base):
    __tablename__ = "project_references"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    authors: Mapped[str | None] = mapped_column(String(512))
    title: Mapped[str] = mapped_column(String(512))
    source: Mapped[str | None] = mapped_column(String(512))
    year: Mapped[str | None] = mapped_column(String(32))
    extra: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    project: Mapped[Project] = relationship(back_populates="references")


class Chapter(TimestampMixin, Base):
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    level: Mapped[int] = mapped_column(Integer)
    order: Mapped[int] = mapped_column(Integer)
    purpose: Mapped[str | None] = mapped_column(Text)
    suggested_word_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        Enum(*CHAPTER_STATUSES, name="chapter_status"), default="planned"
    )

    project: Mapped[Project] = relationship(back_populates="chapters")
    parent: Mapped["Chapter | None"] = relationship(remote_side="Chapter.id", back_populates="children")
    children: Mapped[list["Chapter"]] = relationship(back_populates="parent", cascade="all, delete-orphan")
    relation: Mapped["ChapterRelation | None"] = relationship(
        back_populates="chapter", cascade="all, delete-orphan", uselist=False
    )
    drafts: Mapped[list["ChapterDraft"]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan"
    )
    summaries: Mapped[list["ChapterSummary"]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan"
    )
    feedback_items: Mapped[list["FeedbackItem"]] = relationship(back_populates="chapter")
    consistency_issues: Mapped[list["ConsistencyIssue"]] = relationship(back_populates="chapter")


class ChapterRelation(TimestampMixin, Base):
    __tablename__ = "chapter_relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    chapter_id: Mapped[str] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), unique=True)
    previous_bridge: Mapped[str | None] = mapped_column(Text)
    next_bridge: Mapped[str | None] = mapped_column(Text)
    required_questions: Mapped[list[str] | None] = mapped_column(JSON)
    depends_on_facts: Mapped[list[str] | None] = mapped_column(JSON)
    key_points: Mapped[list[str] | None] = mapped_column(JSON)
    output_conclusions: Mapped[list[str] | None] = mapped_column(JSON)
    avoid_repeating: Mapped[list[str] | None] = mapped_column(JSON)

    chapter: Mapped[Chapter] = relationship(back_populates="relation")


class ChapterDraft(Base):
    __tablename__ = "chapter_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    chapter_id: Mapped[str] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    prompt_snapshot: Mapped[dict | None] = mapped_column(JSON)
    generation_mode: Mapped[str] = mapped_column(Enum(*DRAFT_MODES, name="draft_mode"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    chapter: Mapped[Chapter] = relationship(back_populates="drafts")


class ChapterSummary(TimestampMixin, Base):
    __tablename__ = "chapter_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    chapter_id: Mapped[str] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"))
    summary: Mapped[str] = mapped_column(Text)
    key_conclusions: Mapped[list[str] | None] = mapped_column(JSON)
    used_facts: Mapped[list[str] | None] = mapped_column(JSON)
    forward_implications: Mapped[list[str] | None] = mapped_column(JSON)

    chapter: Mapped[Chapter] = relationship(back_populates="summaries")


class Material(TimestampMixin, Base):
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(Enum(*MATERIAL_TYPES, name="material_type"))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str | None] = mapped_column(Text)
    file_url: Mapped[str | None] = mapped_column(String(2048))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)

    project: Mapped[Project] = relationship(back_populates="materials")


class FeedbackItem(TimestampMixin, Base):
    __tablename__ = "feedback_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    chapter_id: Mapped[str | None] = mapped_column(ForeignKey("chapters.id", ondelete="SET NULL"))
    raw_text: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        Enum(*FEEDBACK_STATUSES, name="feedback_status"), default="open"
    )
    suggestion: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project] = relationship(back_populates="feedback_items")
    chapter: Mapped[Chapter | None] = relationship(back_populates="feedback_items")


class ConsistencyIssue(TimestampMixin, Base):
    __tablename__ = "consistency_issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    chapter_id: Mapped[str | None] = mapped_column(ForeignKey("chapters.id", ondelete="SET NULL"))
    severity: Mapped[str] = mapped_column(Enum(*ISSUE_SEVERITIES, name="issue_severity"))
    type: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Enum(*ISSUE_STATUSES, name="issue_status"), default="open"
    )

    project: Mapped[Project] = relationship(back_populates="consistency_issues")
    chapter: Mapped[Chapter | None] = relationship(back_populates="consistency_issues")


class ExportRecord(Base):
    __tablename__ = "export_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    format: Mapped[str] = mapped_column(Enum(*EXPORT_FORMATS, name="export_format"))
    file_url: Mapped[str] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="export_records")
