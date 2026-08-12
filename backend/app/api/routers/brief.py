from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import ProjectContext
from app.db.session import get_db
from app.schemas.workflow import (
    ProjectBriefRead,
    ProjectBriefUpdate,
    ProjectContextPayload,
    ProjectContextRead,
)
from app.services.generation import GenerationService
from app.services.projects import ProjectService

router = APIRouter(prefix="/api/projects/{project_id}", tags=["brief"])
DbSession = Annotated[Session, Depends(get_db)]


@router.put("/context", response_model=ProjectContextRead)
def save_context(project_id: str, payload: ProjectContextPayload, db: DbSession) -> ProjectContext:
    project = ProjectService.get_project_or_404(db, project_id)
    context = project.context or ProjectContext(project_id=project.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(context, field, value)
    db.add(context)
    db.commit()
    db.refresh(context)
    return context


@router.get("/context", response_model=ProjectContextRead)
def get_context(project_id: str, db: DbSession) -> ProjectContext:
    project = ProjectService.get_project_or_404(db, project_id)
    if project.context is None:
        raise HTTPException(status_code=404, detail="Project context not found")
    return project.context


@router.post("/brief/generate", response_model=ProjectBriefRead)
def generate_brief(project_id: str, db: DbSession):
    return GenerationService.generate_brief(db, project_id)


@router.get("/brief", response_model=ProjectBriefRead)
def get_brief(project_id: str, db: DbSession):
    project = ProjectService.get_project_or_404(db, project_id)
    if project.brief is None:
        raise HTTPException(status_code=404, detail="Project brief not found")
    return project.brief


@router.patch("/brief", response_model=ProjectBriefRead)
def update_brief(project_id: str, payload: ProjectBriefUpdate, db: DbSession):
    project = ProjectService.get_project_or_404(db, project_id)
    if project.brief is None:
        raise HTTPException(status_code=404, detail="Project brief not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project.brief, field, value)
    db.commit()
    db.refresh(project.brief)
    return project.brief
