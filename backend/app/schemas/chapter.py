from pydantic import BaseModel, Field


class ChapterGeneration(BaseModel):
    title: str
    level: int = 1
    order: int
    purpose: str | None = None
    suggested_word_count: int | None = None
    children: list["ChapterGeneration"] = Field(default_factory=list)


class OutlineGeneration(BaseModel):
    chapters: list[ChapterGeneration]


class ChapterRelationGeneration(BaseModel):
    chapter_title: str
    purpose: str | None = None
    previous_bridge: str | None = None
    next_bridge: str | None = None
    required_questions: list[str] = Field(default_factory=list)
    depends_on_facts: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    output_conclusions: list[str] = Field(default_factory=list)
    avoid_repeating: list[str] = Field(default_factory=list)


class RelationsGeneration(BaseModel):
    relations: list[ChapterRelationGeneration]


class ChapterSummaryGeneration(BaseModel):
    summary: str
    key_conclusions: list[str] = Field(default_factory=list)
    used_facts: list[str] = Field(default_factory=list)
    forward_implications: list[str] = Field(default_factory=list)
