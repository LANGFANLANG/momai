from pathlib import Path

from docx import Document

from app.db.models import Chapter, ChapterDraft, Project


def build_docx(
    output_path: Path, project: Project, chapters: list[Chapter], drafts: dict[str, ChapterDraft]
) -> None:
    document = Document()
    document.add_heading(project.title, level=0)
    for chapter in chapters:
        document.add_heading(chapter.title, level=min(max(chapter.level, 1), 9))
        draft = drafts.get(chapter.id)
        if draft:
            for paragraph in draft.content.splitlines():
                if paragraph.strip():
                    document.add_paragraph(paragraph)
    document.save(output_path)
