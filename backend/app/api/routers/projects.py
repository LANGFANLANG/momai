from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.projects import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: DbSession, user: CurrentUser) -> ProjectRead:
    return ProjectService.create_project(db, payload, user)


@router.get("", response_model=list[ProjectRead])
def list_projects(db: DbSession, user: CurrentUser) -> list[ProjectRead]:
    return ProjectService.list_projects(db, user)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: DbSession, user: CurrentUser) -> ProjectRead:
    return ProjectService.get_project_or_404(db, project_id, user)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(project_id: str, payload: ProjectUpdate, db: DbSession, user: CurrentUser) -> ProjectRead:
    return ProjectService.update_project(db, project_id, payload, user)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: DbSession, user: CurrentUser) -> Response:
    ProjectService.delete_project(db, project_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
