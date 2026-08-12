from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chapter


def order_chapters_in_hierarchy(chapters: list[Chapter]) -> list[Chapter]:
    """Flatten chapters depth-first while preserving deterministic sibling order."""
    by_id = {chapter.id: chapter for chapter in chapters}
    children: dict[str, list[Chapter]] = {}
    roots: list[Chapter] = []
    sort_key = lambda chapter: (chapter.order, chapter.level, chapter.id)

    for chapter in chapters:
        if chapter.parent_id and chapter.parent_id in by_id:
            children.setdefault(chapter.parent_id, []).append(chapter)
        else:
            roots.append(chapter)

    ordered: list[Chapter] = []
    visited: set[str] = set()

    def visit(chapter: Chapter) -> None:
        if chapter.id in visited:
            return
        visited.add(chapter.id)
        ordered.append(chapter)
        for child in sorted(children.get(chapter.id, []), key=sort_key):
            visit(child)

    for root in sorted(roots, key=sort_key):
        visit(root)
    for chapter in sorted(chapters, key=sort_key):
        visit(chapter)
    return ordered


def list_chapters_in_hierarchy_order(db: Session, project_id: str) -> list[Chapter]:
    chapters = list(db.scalars(select(Chapter).where(Chapter.project_id == project_id)))
    return order_chapters_in_hierarchy(chapters)
