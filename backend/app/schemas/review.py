from typing import Literal

from pydantic import BaseModel, Field


class ConsistencyIssueGeneration(BaseModel):
    severity: Literal["low", "medium", "high"] = "low"
    type: str
    chapter_title: str | None = None
    description: str
    suggestion: str | None = None


class ConsistencyReviewGeneration(BaseModel):
    issues: list[ConsistencyIssueGeneration] = Field(default_factory=list)
    overall_suggestion: str | None = None
