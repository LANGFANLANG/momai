from app.db.models import Chapter, ChapterDraft, Project
from app.export.common import chapters_by_id, covered_by_ancestor_draft, draft_body


def build_markdown(project: Project, chapters: list[Chapter], drafts: dict[str, ChapterDraft]) -> str:
    by_id = chapters_by_id(chapters)
    sections = [f"# {project.title}"]
    for chapter in chapters:
        if covered_by_ancestor_draft(chapter, by_id, drafts):
            continue
        sections.append(f"{'#' * max(chapter.level, 1)} {chapter.title}")
        draft = drafts.get(chapter.id)
        if draft:
            content = draft_body(chapter, draft)
            if content:
                sections.append(content)
    return "\n\n".join(sections) + "\n"
