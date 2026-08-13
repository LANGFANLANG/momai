from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import re


def _coerce_optional_int(value) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+", value.replace(",", ""))
        return int(match.group(0)) if match else None
    return None


class ChapterGeneration(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    level: int = 1
    order: int = 0
    purpose: str | None = None
    suggested_word_count: int | None = None
    children: list["ChapterGeneration"] = Field(default_factory=list)

    @field_validator("title", mode="before")
    @classmethod
    def coerce_title(cls, value):
        text = str(value).strip() if value is not None else ""
        return text or "未命名章节"

    @field_validator("level", mode="before")
    @classmethod
    def coerce_level(cls, value):
        return _coerce_optional_int(value) or 1

    @field_validator("order", mode="before")
    @classmethod
    def coerce_order(cls, value):
        return _coerce_optional_int(value) or 0

    @field_validator("suggested_word_count", mode="before")
    @classmethod
    def coerce_word_count(cls, value):
        return _coerce_optional_int(value)

    @field_validator("purpose", mode="before")
    @classmethod
    def coerce_purpose(cls, value):
        if value is None:
            return None
        if isinstance(value, list):
            return "；".join(str(item) for item in value if item)
        return str(value)

    @field_validator("children", mode="before")
    @classmethod
    def coerce_children(cls, value):
        return [] if value is None else value


class OutlineGeneration(BaseModel):
    chapters: list[ChapterGeneration]

    @model_validator(mode="before")
    @classmethod
    def unwrap_chapters(cls, value):
        if isinstance(value, list):
            return {"chapters": value}
        if not isinstance(value, dict):
            return value
        if isinstance(value.get("chapters"), list):
            return value
        for key in ("outline", "data", "result"):
            inner = value.get(key)
            if isinstance(inner, list):
                return {"chapters": inner}
            if isinstance(inner, dict) and isinstance(inner.get("chapters"), list):
                return inner
        return value

    @model_validator(mode="after")
    def fill_missing_orders(self):
        def walk(items: list[ChapterGeneration]) -> None:
            for index, item in enumerate(items, start=1):
                if not item.order:
                    item.order = index
                walk(item.children)

        walk(self.chapters)
        return self


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
