from pathlib import Path
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Chapter, ChapterDraft, ExportRecord
from app.export.docx import build_docx
from app.export.docx_style import resolve_docx_style
from app.export.markdown import build_markdown
from app.services.chapters import list_chapters_in_hierarchy_order
from app.services.projects import ProjectService

_UNSAFE_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_export_stem(title: str) -> str:
    stem = _UNSAFE_FILENAME.sub("", (title or "").replace("\n", " "))
    stem = re.sub(r"\s+", " ", stem).strip(" .")
    stem = stem[:120].rstrip(" .")
    return stem or "export"


def download_filename(title: str, suffix: str) -> str:
    if not suffix.startswith("."):
        suffix = f".{suffix}"
    return f"{sanitize_export_stem(title)}{suffix}"


class ExportService:
    @staticmethod
    def _export_dir() -> Path:
        directory = Path(get_settings().export_dir)
        directory.mkdir(parents=True, exist_ok=True)
        return directory.resolve()

    @classmethod
    def _output_path(cls, title: str, record_id: str, suffix: str) -> Path:
        if not suffix.startswith("."):
            suffix = f".{suffix}"
        directory = cls._export_dir()
        preferred = directory / download_filename(title, suffix)
        if not preferred.exists():
            return preferred
        return directory / f"{sanitize_export_stem(title)}-{record_id[:8]}{suffix}"

    @staticmethod
    def _chapters_and_drafts(db: Session, project_id: str):
        chapters = list_chapters_in_hierarchy_order(db, project_id)
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
        output_path = cls._output_path(project.title, record.id, ".md")
        output_path.write_text(
            build_markdown(project, chapters, drafts, project.paper_abstract),
            encoding="utf-8",
        )
        record.file_url = str(output_path)
        project.status = "export_ready"
        db.commit()
        db.refresh(record)
        return record

    @classmethod
    def export_docx(cls, db: Session, project_id: str, style_override: dict | None = None) -> ExportRecord:
        project = ProjectService.get_project_or_404(db, project_id)
        chapters, drafts = cls._chapters_and_drafts(db, project.id)
        record = ExportRecord(project_id=project.id, format="docx", file_url="")
        db.add(record)
        db.flush()
        output_path = cls._output_path(project.title, record.id, ".docx")
        build_docx(
            output_path,
            project,
            chapters,
            drafts,
            resolve_docx_style(project, style_override),
            project.paper_abstract,
        )
        record.file_url = str(output_path)
        project.status = "export_ready"
        db.commit()
        db.refresh(record)
        return record
