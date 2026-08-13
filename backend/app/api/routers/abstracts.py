from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import PaperAbstract, User
from app.db.session import get_db
from app.schemas.workflow import PaperAbstractRead, PaperAbstractUpdate
from app.services.generation import ChapterDraftRequired, GenerationService
from app.services.projects import ProjectService

router = APIRouter(prefix="/api/projects/{project_id}", tags=["abstract"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.get("/abstract", response_model=PaperAbstractRead)
def get_abstract(project_id: str, db: DbSession, user: CurrentUser):
    project = ProjectService.get_project_or_404(db, project_id, user)
    if project.paper_abstract is None:
        raise HTTPException(status_code=404, detail="Paper abstract not found")
    return project.paper_abstract


@router.patch("/abstract", response_model=PaperAbstractRead)
def update_abstract(project_id: str, payload: PaperAbstractUpdate, db: DbSession, user: CurrentUser):
    project = ProjectService.get_project_or_404(db, project_id, user)
    abstract = project.paper_abstract or PaperAbstract(project_id=project.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(abstract, field, value)
    db.add(abstract)
    db.commit()
    db.refresh(abstract)
    return abstract


@router.post("/abstract/generate", response_model=PaperAbstractRead)
def generate_abstract(project_id: str, db: DbSession, user: CurrentUser):
    ProjectService.get_project_or_404(db, project_id, user)
    try:
        return GenerationService.generate_paper_abstract(db, project_id)
    except ChapterDraftRequired as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
