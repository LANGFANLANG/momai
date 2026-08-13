from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.codebase import (
    CodebaseAnalysisRead,
    CodebaseAnalyzeRequest,
    CodebaseApplyRead,
    CodebaseApplyRequest,
)
from app.services.codebase_analyzer import CodebaseAnalysisService
from app.services.projects import ProjectService

router = APIRouter(prefix="/api/projects/{project_id}/codebase", tags=["codebase"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.post("/analyze", response_model=CodebaseAnalysisRead)
def analyze_codebase(
    project_id: str,
    payload: CodebaseAnalyzeRequest,
    db: DbSession,
    user: CurrentUser,
) -> CodebaseAnalysisRead:
    project = ProjectService.get_project_or_404(db, project_id, user)
    try:
        return CodebaseAnalysisService.analyze_path(
            Path(payload.root_path),
            project_title=project.title,
            user_hint=payload.user_hint,
            include_tests=payload.include_tests,
            include_docs=payload.include_docs,
            max_files=payload.max_files,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="本地项目路径不存在，请检查路径是否正确。") from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail="当前进程没有权限读取该目录。") from error


@router.post("/apply", response_model=CodebaseApplyRead)
def apply_codebase_analysis(
    project_id: str,
    payload: CodebaseApplyRequest,
    db: DbSession,
    user: CurrentUser,
) -> CodebaseApplyRead:
    ProjectService.get_project_or_404(db, project_id, user)
    result = CodebaseAnalysisService.apply_to_project(
        db,
        project_id,
        payload.analysis,
        update_project_context=payload.update_project_context,
        update_project_brief=payload.update_project_brief,
        create_material=payload.create_material,
    )
    return CodebaseApplyRead(
        material_id=result.material.id if result.material else None,
        brief_updated=result.brief_updated,
        context_updated=result.context_updated,
        locked_facts_added=result.locked_facts_added,
    )
