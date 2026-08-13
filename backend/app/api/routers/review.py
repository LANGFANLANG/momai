from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import ConsistencyIssue, User
from app.db.session import get_db
from app.schemas.workflow import ConsistencyFixRead, ConsistencyIssueRead, ConsistencyIssueUpdate
from app.services.generation import ConsistencyFixConflict, ConsistencyFixFailed, GenerationService
from app.services.projects import ProjectService

router = APIRouter(prefix="/api/projects/{project_id}/review", tags=["review"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.post("/generate", response_model=list[ConsistencyIssueRead])
def generate_review(project_id: str, db: DbSession, user: CurrentUser):
    ProjectService.get_project_or_404(db, project_id, user)
    return GenerationService.review_consistency(db, project_id)


@router.get("", response_model=list[ConsistencyIssueRead])
def list_issues(project_id: str, db: DbSession, user: CurrentUser):
    ProjectService.get_project_or_404(db, project_id, user)
    return list(db.scalars(select(ConsistencyIssue).where(ConsistencyIssue.project_id == project_id).order_by(ConsistencyIssue.created_at.desc())))


@router.post("/{issue_id}/fix", response_model=ConsistencyFixRead)
def fix_issue(project_id: str, issue_id: str, db: DbSession, user: CurrentUser):
    ProjectService.get_project_or_404(db, project_id, user)
    try:
        issue, drafts, fix_summary = GenerationService.fix_consistency_issue(
            db, project_id, issue_id
        )
    except ConsistencyFixConflict as error:
        status_code = 404 if str(error) == "Consistency issue not found" else 409
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    except ConsistencyFixFailed as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return ConsistencyFixRead(issue=issue, drafts=drafts, fix_summary=fix_summary)


@router.patch("/{issue_id}", response_model=ConsistencyIssueRead)
def update_issue(project_id: str, issue_id: str, payload: ConsistencyIssueUpdate, db: DbSession, user: CurrentUser):
    ProjectService.get_project_or_404(db, project_id, user)
    issue = db.get(ConsistencyIssue, issue_id)
    if issue is None or issue.project_id != project_id:
        raise HTTPException(status_code=404, detail="Consistency issue not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(issue, field, value)
    db.commit()
    db.refresh(issue)
    return issue
