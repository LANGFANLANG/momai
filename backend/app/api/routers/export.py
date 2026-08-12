from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.models import ExportRecord
from app.db.session import get_db
from app.schemas.workflow import ExportRecordRead
from app.services.export import ExportService

router = APIRouter(tags=["export"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/api/projects/{project_id}/export/markdown", response_model=ExportRecordRead)
def export_markdown(project_id: str, db: DbSession):
    return ExportService.export_markdown(db, project_id)


@router.post("/api/projects/{project_id}/export/docx", response_model=ExportRecordRead)
def export_docx(project_id: str, db: DbSession):
    return ExportService.export_docx(db, project_id)


@router.get("/api/exports/{export_id}/download")
def download_export(export_id: str, db: DbSession) -> FileResponse:
    record = db.get(ExportRecord, export_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Export not found")
    file_path = Path(record.file_url)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Export file not found")
    return FileResponse(file_path, filename=file_path.name)
