from app.db.models import Chapter, ChapterDraft
from app.services.markdown_sections import extract_markdown_section, titles_match


def chapters_by_id(chapters: list[Chapter]) -> dict[str, Chapter]:
    return {chapter.id: chapter for chapter in chapters}


def ancestor_chain(chapter: Chapter, by_id: dict[str, Chapter]) -> list[Chapter]:
    ancestors: list[Chapter] = []
    current = chapter
    while current.parent_id:
        parent = by_id.get(current.parent_id)
        if parent is None:
            break
        ancestors.append(parent)
        current = parent
    return ancestors


def covered_by_ancestor_draft(
    chapter: Chapter,
    by_id: dict[str, Chapter],
    drafts: dict[str, ChapterDraft],
) -> bool:
    if drafts.get(chapter.id):
        return False
    for ancestor in ancestor_chain(chapter, by_id):
        draft = drafts.get(ancestor.id)
        if draft and extract_markdown_section(draft.content, chapter.title, chapter.level):
            return True
    return False


def heading_matches_chapter(line: str, chapter: Chapter) -> bool:
    stripped = line.strip()
    if not stripped.startswith("#"):
        return False
    title = stripped.lstrip("#").strip().rstrip("#").strip()
    return titles_match(title, chapter.title)


def draft_body(chapter: Chapter, draft: ChapterDraft) -> str:
    lines = draft.content.splitlines()
    if lines and heading_matches_chapter(lines[0], chapter):
        lines = lines[1:]
        if lines and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(lines).strip()
