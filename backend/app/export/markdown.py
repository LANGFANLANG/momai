from app.db.models import Chapter, ChapterDraft, PaperAbstract, Project
from app.export.common import (
    abstract_has_content,
    chapters_by_id,
    covered_by_ancestor_draft,
    draft_body,
    join_keywords,
)


def _abstract_markdown(abstract: PaperAbstract | None) -> list[str]:
    if not abstract_has_content(abstract) or abstract is None:
        return []
    sections: list[str] = []
    if (abstract.abstract_zh or "").strip():
        sections.append("# 摘要")
        sections.append(abstract.abstract_zh.strip())
        keywords = join_keywords(abstract.keywords_zh, chinese=True)
        if keywords:
            sections.append(f"关键词：{keywords}")
    if (abstract.abstract_en or "").strip() or (abstract.title_en or "").strip():
        sections.append("# Abstract")
        if (abstract.title_en or "").strip():
            sections.append(abstract.title_en.strip())
        if (abstract.abstract_en or "").strip():
            sections.append(abstract.abstract_en.strip())
        keywords = join_keywords(abstract.keywords_en, chinese=False)
        if keywords:
            sections.append(f"Keywords: {keywords}")
    return sections


def build_markdown(
    project: Project,
    chapters: list[Chapter],
    drafts: dict[str, ChapterDraft],
    paper_abstract: PaperAbstract | None = None,
) -> str:
    by_id = chapters_by_id(chapters)
    sections = [f"# {project.title}", *_abstract_markdown(paper_abstract)]
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
