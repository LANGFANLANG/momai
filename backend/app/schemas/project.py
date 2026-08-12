from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.db.models import PROJECT_STATUSES, PROJECT_TYPES

ProjectType = Literal[*PROJECT_TYPES]
ProjectStatus = Literal[*PROJECT_STATUSES]


class ProjectCreate(BaseModel):
    type: ProjectType
    title: str
    major: str | None = None
    school: str | None = None
    target_word_count: int | None = None
    language: str
    requirements: str | None = None


class ProjectUpdate(BaseModel):
    type: ProjectType = None
    title: str = None
    major: str | None = None
    school: str | None = None
    target_word_count: int | None = None
    language: str = None
    requirements: str | None = None
    status: ProjectStatus = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: ProjectType
    title: str
    major: str | None
    school: str | None
    target_word_count: int | None
    language: str
    requirements: str | None
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
