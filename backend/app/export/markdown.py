import re

from app.db.models import Chapter, ChapterDraft, Project


def build_markdown(project: Project, chapters: list[Chapter], drafts: dict[str, ChapterDraft]) -> str:
    sections = [f"# {project.title}"]
    for chapter in chapters:
        heading = f"{'#' * max(chapter.level, 1)} {chapter.title}"
        sections.append(heading)
        draft = drafts.get(chapter.id)
        if draft:
            lines = draft.content.splitlines()
            first_line_is_chapter_heading = bool(
                lines
                and re.fullmatch(
                    rf"#+\s+{re.escape(chapter.title)}\s*#*",
                    lines[0].strip(),
                )
            )
            if first_line_is_chapter_heading:
                lines = lines[1:]
                if lines and not lines[0].strip():
                    lines = lines[1:]
            content = "\n".join(lines)
            if content:
                sections.append(content)
    return "\n\n".join(sections) + "\n"
