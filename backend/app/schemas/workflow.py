from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import DRAFT_MODES, ISSUE_STATUSES


class ProjectContextPayload(BaseModel):
    background: str | None = None
    problem: str | None = None
    goal: str | None = None
    scenario: str | None = None
    target_users: str | None = None
    methods: list[str] | None = None
    technologies: list[str] | None = None
    modules: list[str] | None = None
    architecture: str | None = None
    environment: str | None = None
    data_sources: list[str] | None = None
    experiments: str | None = None
    innovations: list[str] | None = None
    constraints: list[str] | None = None
    writing_prefs: dict | None = None


class ProjectContextRead(ProjectContextPayload):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str


class ProjectBriefRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title_explanation: str | None
    background: str | None
    core_problem: str | None
    goal: str | None
    significance: str | None
    technical_route: str | None
    modules: list[str] | None
    expected_result: str | None
    writing_boundary: str | None
    missing_info: list[str] | None
    locked_facts: list[str] | None


class ProjectBriefUpdate(BaseModel):
    title_explanation: str | None = None
    background: str | None = None
    core_problem: str | None = None
    goal: str | None = None
    significance: str | None = None
    technical_route: str | None = None
    modules: list[str] | None = None
    expected_result: str | None = None
    writing_boundary: str | None = None
    missing_info: list[str] | None = None
    locked_facts: list[str] | None = None


class OutlineGenerateRequest(BaseModel):
    outline_preference: str | None = None


class ChapterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    parent_id: str | None
    title: str
    level: int
    order: int
    purpose: str | None
    suggested_word_count: int | None
    status: str


class ChapterUpdate(BaseModel):
    title: str | None = None
    level: int | None = None
    order: int | None = None
    purpose: str | None = None
    suggested_word_count: int | None = None
    status: str | None = None


class ChapterRelationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chapter_id: str
    previous_bridge: str | None
    next_bridge: str | None
    required_questions: list[str] | None
    depends_on_facts: list[str] | None
    key_points: list[str] | None
    output_conclusions: list[str] | None
    avoid_repeating: list[str] | None


class ChapterRelationUpdate(BaseModel):
    previous_bridge: str | None = None
    next_bridge: str | None = None
    required_questions: list[str] | None = None
    depends_on_facts: list[str] | None = None
    key_points: list[str] | None = None
    output_conclusions: list[str] | None = None
    avoid_repeating: list[str] | None = None


class DraftGenerateRequest(BaseModel):
    mode: Literal[*DRAFT_MODES] = "generate"
    user_instruction: str | None = None


class ChapterDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chapter_id: str
    version: int
    content: str
    prompt_snapshot: dict | None
    generation_mode: str
    created_at: datetime


class ChapterSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chapter_id: str
    summary: str
    key_conclusions: list[str] | None
    used_facts: list[str] | None
    forward_implications: list[str] | None


class ConsistencyIssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    chapter_id: str | None
    severity: str
    type: str
    description: str
    suggestion: str | None
    status: str


class ConsistencyIssueUpdate(BaseModel):
    severity: Literal["low", "medium", "high"] | None = None
    type: str | None = None
    description: str | None = None
    suggestion: str | None = None
    status: Literal[*ISSUE_STATUSES] | None = None


class ExportRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    format: str
    file_url: str
    created_at: datetime
