from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chapter, ChapterDraft
from app.db.session import get_db
from app.schemas.workflow import ChapterDraftRead, ChapterSummaryRead, DraftGenerateRequest
from app.services.generation import GenerationService

router = APIRouter(prefix="/api/chapters", tags=["chapters"])
DbSession = Annotated[Session, Depends(get_db)]


def _chapter_or_404(db: Session, chapter_id: str) -> Chapter:
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


@router.post("/{chapter_id}/drafts/generate", response_model=ChapterDraftRead)
def generate_draft(chapter_id: str, payload: DraftGenerateRequest, db: DbSession):
    _chapter_or_404(db, chapter_id)
    return GenerationService.generate_draft(db, chapter_id, payload.mode, payload.user_instruction)


@router.get("/{chapter_id}/drafts", response_model=list[ChapterDraftRead])
def list_drafts(chapter_id: str, db: DbSession):
    _chapter_or_404(db, chapter_id)
    return list(db.scalars(select(ChapterDraft).where(ChapterDraft.chapter_id == chapter_id).order_by(ChapterDraft.version.desc())))


@router.post("/{chapter_id}/summary/generate", response_model=ChapterSummaryRead)
def generate_summary(chapter_id: str, db: DbSession):
    _chapter_or_404(db, chapter_id)
    return GenerationService.generate_summary(db, chapter_id)
