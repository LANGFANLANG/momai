from pydantic import BaseModel, ConfigDict, Field


class CodebaseAnalyzeRequest(BaseModel):
    root_path: str
    include_tests: bool = False
    include_docs: bool = True
    max_files: int = Field(default=120, ge=1, le=500)
    user_hint: str | None = None


class FileTreeSummary(BaseModel):
    root: str
    total_files: int
    included_files: list[str]
    ignored_summary: dict[str, int] = Field(default_factory=dict)


class CodebaseFactRead(BaseModel):
    category: str
    title: str
    content: str
    evidence_files: list[str]
    confidence: str
    chapter_tags: list[str]


class CodebaseAnalysisRead(BaseModel):
    summary: str
    tech_stack: dict[str, list[str]]
    file_tree: FileTreeSummary
    facts: list[CodebaseFactRead]
    missing_info: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CodebaseApplyRequest(BaseModel):
    update_project_context: bool = True
    update_project_brief: bool = True
    create_material: bool = True
    analysis: CodebaseAnalysisRead


class CodebaseApplyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    material_id: str | None = None
    brief_updated: bool
    context_updated: bool
    locked_facts_added: int
