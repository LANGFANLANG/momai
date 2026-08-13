import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.models import ExportRecord
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.workflow import ExportRecordRead
from app.services.export import ExportService, download_filename

router = APIRouter(tags=["export"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/api/projects/{project_id}/export/markdown", response_model=ExportRecordRead)
def export_markdown(project_id: str, db: DbSession):
    return ExportService.export_markdown(db, project_id)


@router.post("/api/projects/{project_id}/export/docx", response_model=ExportRecordRead)
async def export_docx(project_id: str, request: Request, db: DbSession):
    override = None
    raw = await request.body()
    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            override = payload.get("style")
    return ExportService.export_docx(db, project_id, override)


@router.get("/api/exports/{export_id}/download")
def download_export(export_id: str, db: DbSession) -> FileResponse:
    record = db.get(ExportRecord, export_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Export not found")
    export_dir = Path(get_settings().export_dir).resolve()
    file_path = Path(record.file_url).resolve()
    if not file_path.is_relative_to(export_dir):
        raise HTTPException(status_code=404, detail="Export file not found")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Export file not found")
    return FileResponse(
        file_path,
        filename=download_filename(record.project.title, file_path.suffix),
    )
