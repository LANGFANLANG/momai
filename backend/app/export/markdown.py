from app.db.models import Chapter, ChapterDraft, Project


def build_markdown(project: Project, chapters: list[Chapter], drafts: dict[str, ChapterDraft]) -> str:
    sections = [f"# {project.title}"]
    for chapter in chapters:
        sections.append(f"{'#' * max(chapter.level, 1)} {chapter.title}")
        draft = drafts.get(chapter.id)
        if draft:
            sections.append(draft.content)
    return "\n\n".join(sections) + "\n"
