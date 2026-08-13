from typing import Annotated
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import Chapter, User
from app.db.session import get_db
from app.schemas.workflow import ChapterRead, ChapterUpdate, OutlineGenerateRequest
from app.services.chapters import list_chapters_in_hierarchy_order
from app.services.generation import (
    GenerationService,
    OutlineGenerationFailed,
    OutlineRegenerationConflict,
)
from app.services.projects import ProjectService

router = APIRouter(prefix="/api/projects/{project_id}/outline", tags=["outline"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=list[ChapterRead])
def generate_outline(project_id: str, payload: OutlineGenerateRequest, db: DbSession, user: CurrentUser):
    ProjectService.get_project_or_404(db, project_id, user)
    try:
        return GenerationService.generate_outline(
            db,
            project_id,
            outline_preference=payload.outline_preference,
            force=payload.force,
        )
    except HTTPException:
        raise
    except OutlineRegenerationConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except OutlineGenerationFailed as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except Exception as error:
        logger.exception("Outline generation failed")
        raise HTTPException(status_code=502, detail=f"大纲生成失败：{error}") from error


@router.get("", response_model=list[ChapterRead])
def list_outline(project_id: str, db: DbSession, user: CurrentUser):
    ProjectService.get_project_or_404(db, project_id, user)
    GenerationService.sync_matched_child_draft_statuses(db, project_id)
    return list_chapters_in_hierarchy_order(db, project_id)


@router.patch("/{chapter_id}", response_model=ChapterRead)
def update_chapter(project_id: str, chapter_id: str, payload: ChapterUpdate, db: DbSession, user: CurrentUser):
    ProjectService.get_project_or_404(db, project_id, user)
    chapter = db.get(Chapter, chapter_id)
    if chapter is None or chapter.project_id != project_id:
        raise HTTPException(status_code=404, detail="Chapter not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(chapter, field, value)
    db.commit()
    db.refresh(chapter)
    return chapter
