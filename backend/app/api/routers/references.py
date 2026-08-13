from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import ProjectReference, User
from app.db.session import get_db
from app.schemas.workflow import ProjectReferenceCreate, ProjectReferenceRead, ProjectReferenceUpdate
from app.services.projects import ProjectService

router = APIRouter(prefix="/api/projects/{project_id}/references", tags=["references"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


def _get_reference_or_404(db: Session, project_id: str, reference_id: str) -> ProjectReference:
    reference = db.get(ProjectReference, reference_id)
    if reference is None or reference.project_id != project_id:
        raise HTTPException(status_code=404, detail="Reference not found")
    return reference


@router.get("", response_model=list[ProjectReferenceRead])
def list_references(project_id: str, db: DbSession, user: CurrentUser):
    ProjectService.get_project_or_404(db, project_id, user)
    return list(
        db.scalars(
            select(ProjectReference)
            .where(ProjectReference.project_id == project_id)
            .order_by(ProjectReference.sort_order, ProjectReference.created_at)
        )
    )


@router.post("", response_model=ProjectReferenceRead, status_code=status.HTTP_201_CREATED)
def create_reference(project_id: str, payload: ProjectReferenceCreate, db: DbSession, user: CurrentUser):
    ProjectService.get_project_or_404(db, project_id, user)
    next_order = db.scalar(
        select(func.coalesce(func.max(ProjectReference.sort_order), 0)).where(
            ProjectReference.project_id == project_id
        )
    )
    reference = ProjectReference(
        project_id=project_id,
        sort_order=(next_order or 0) + 1,
        **payload.model_dump(),
    )
    db.add(reference)
    db.commit()
    db.refresh(reference)
    return reference


@router.patch("/{reference_id}", response_model=ProjectReferenceRead)
def update_reference(
    project_id: str, reference_id: str, payload: ProjectReferenceUpdate, db: DbSession, user: CurrentUser
):
    ProjectService.get_project_or_404(db, project_id, user)
    reference = _get_reference_or_404(db, project_id, reference_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reference, field, value)
    db.commit()
    db.refresh(reference)
    return reference


@router.delete("/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference(project_id: str, reference_id: str, db: DbSession, user: CurrentUser) -> Response:
    ProjectService.get_project_or_404(db, project_id, user)
    reference = _get_reference_or_404(db, project_id, reference_id)
    db.delete(reference)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
