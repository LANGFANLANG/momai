from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Chapter
from app.db.session import get_db
from app.schemas.workflow import ChapterRead, ChapterUpdate, OutlineGenerateRequest
from app.services.chapters import list_chapters_in_hierarchy_order
from app.services.generation import GenerationService, OutlineRegenerationConflict
from app.services.projects import ProjectService

router = APIRouter(prefix="/api/projects/{project_id}/outline", tags=["outline"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/generate", response_model=list[ChapterRead])
def generate_outline(project_id: str, payload: OutlineGenerateRequest, db: DbSession):
    try:
        return GenerationService.generate_outline(
            db,
            project_id,
            outline_preference=payload.outline_preference,
            force=payload.force,
        )
    except OutlineRegenerationConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("", response_model=list[ChapterRead])
def list_outline(project_id: str, db: DbSession):
    ProjectService.get_project_or_404(db, project_id)
    return list_chapters_in_hierarchy_order(db, project_id)


@router.patch("/{chapter_id}", response_model=ChapterRead)
def update_chapter(project_id: str, chapter_id: str, payload: ChapterUpdate, db: DbSession):
    chapter = db.get(Chapter, chapter_id)
    if chapter is None or chapter.project_id != project_id:
        raise HTTPException(status_code=404, detail="Chapter not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(chapter, field, value)
    db.commit()
    db.refresh(chapter)
    return chapter
