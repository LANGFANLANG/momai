from pathlib import Path

from docx import Document

from app.db.models import Chapter, ChapterDraft, Project
from app.export.common import chapters_by_id, covered_by_ancestor_draft, draft_body


def build_docx(
    output_path: Path, project: Project, chapters: list[Chapter], drafts: dict[str, ChapterDraft]
) -> None:
    document = Document()
    document.add_heading(project.title, level=0)
    by_id = chapters_by_id(chapters)
    for chapter in chapters:
        if covered_by_ancestor_draft(chapter, by_id, drafts):
            continue
        document.add_heading(chapter.title, level=min(max(chapter.level, 1), 9))
        draft = drafts.get(chapter.id)
        if not draft:
            continue
        for paragraph in draft_body(chapter, draft).splitlines():
            if paragraph.strip():
                document.add_paragraph(paragraph)
    document.save(output_path)
