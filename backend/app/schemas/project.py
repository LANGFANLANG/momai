from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    type: str
    title: str
    major: str | None = None
    school: str | None = None
    target_word_count: int | None = None
    language: str
    requirements: str | None = None


class ProjectUpdate(BaseModel):
    type: str | None = None
    title: str | None = None
    major: str | None = None
    school: str | None = None
    target_word_count: int | None = None
    language: str | None = None
    requirements: str | None = None
    status: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    title: str
    major: str | None
    school: str | None
    target_word_count: int | None
    language: str
    requirements: str | None
    status: str
    created_at: datetime
    updated_at: datetime
