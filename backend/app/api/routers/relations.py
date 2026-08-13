from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import ChapterRelation, User
from app.db.session import get_db
from app.schemas.workflow import ChapterRelationRead, ChapterRelationUpdate
from app.services.chapters import list_chapters_in_hierarchy_order
from app.services.generation import GenerationService
from app.services.projects import ProjectService

router = APIRouter(prefix="/api/projects/{project_id}/relations", tags=["relations"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.post("/generate", response_model=list[ChapterRelationRead])
def generate_relations(project_id: str, db: DbSession, user: CurrentUser):
    ProjectService.get_project_or_404(db, project_id, user)
    return GenerationService.generate_relations(db, project_id)


@router.get("", response_model=list[ChapterRelationRead])
def list_relations(project_id: str, db: DbSession, user: CurrentUser):
    ProjectService.get_project_or_404(db, project_id, user)
    return [
        chapter.relation
        for chapter in list_chapters_in_hierarchy_order(db, project_id)
        if chapter.relation is not None
    ]


@router.patch("/{relation_id}", response_model=ChapterRelationRead)
def update_relation(project_id: str, relation_id: str, payload: ChapterRelationUpdate, db: DbSession, user: CurrentUser):
    ProjectService.get_project_or_404(db, project_id, user)
    relation = db.get(ChapterRelation, relation_id)
    if relation is None or relation.chapter.project_id != project_id:
        raise HTTPException(status_code=404, detail="Chapter relation not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(relation, field, value)
    db.commit()
    db.refresh(relation)
    return relation
