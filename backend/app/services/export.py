from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Chapter, ChapterDraft, ExportRecord
from app.export.docx import build_docx
from app.export.markdown import build_markdown
from app.services.projects import ProjectService


class ExportService:
    @staticmethod
    def _export_dir() -> Path:
        directory = Path(get_settings().export_dir)
        directory.mkdir(parents=True, exist_ok=True)
        return directory.resolve()

    @staticmethod
    def _chapters_and_drafts(db: Session, project_id: str):
        chapters = list(db.scalars(select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.order)))
        drafts: dict[str, ChapterDraft] = {}
        for draft in db.scalars(
            select(ChapterDraft).join(Chapter).where(Chapter.project_id == project_id).order_by(ChapterDraft.version.desc())
        ):
            drafts.setdefault(draft.chapter_id, draft)
        return chapters, drafts

    @classmethod
    def export_markdown(cls, db: Session, project_id: str) -> ExportRecord:
        project = ProjectService.get_project_or_404(db, project_id)
        chapters, drafts = cls._chapters_and_drafts(db, project.id)
        record = ExportRecord(project_id=project.id, format="markdown", file_url="")
        db.add(record)
        db.flush()
        output_path = cls._export_dir() / f"{record.id}.md"
        output_path.write_text(build_markdown(project, chapters, drafts), encoding="utf-8")
        record.file_url = str(output_path)
        project.status = "export_ready"
        db.commit()
        db.refresh(record)
        return record

    @classmethod
    def export_docx(cls, db: Session, project_id: str) -> ExportRecord:
        project = ProjectService.get_project_or_404(db, project_id)
        chapters, drafts = cls._chapters_and_drafts(db, project.id)
        record = ExportRecord(project_id=project.id, format="docx", file_url="")
        db.add(record)
        db.flush()
        output_path = cls._export_dir() / f"{record.id}.docx"
        build_docx(output_path, project, chapters, drafts)
        record.file_url = str(output_path)
        project.status = "export_ready"
        db.commit()
        db.refresh(record)
        return record
