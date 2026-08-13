from pydantic import BaseModel, Field


class PaperAbstractGeneration(BaseModel):
    title_en: str | None = None
    abstract_zh: str
    abstract_en: str
    keywords_zh: list[str] = Field(default_factory=list)
    keywords_en: list[str] = Field(default_factory=list)
