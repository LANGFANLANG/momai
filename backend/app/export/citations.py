from __future__ import annotations

import re
from typing import Iterable

from app.db.models import ProjectReference

CITE_RE = re.compile(r"\[cite:([^\]]+)\]", re.IGNORECASE)
_CHAPTER_PREFIX_RE = re.compile(r"^第[0-9一二三四五六七八九十百]+章")
_BIBLIOGRAPHY_TITLES = {"参考文献", "参考资料", "references", "bibliography"}


def is_bibliography_chapter(title: str | None) -> bool:
    normalized = re.sub(r"\s+", "", title or "")
    normalized = _CHAPTER_PREFIX_RE.sub("", normalized)
    lowered = normalized.lower()
    return lowered in _BIBLIOGRAPHY_TITLES or normalized.endswith("参考文献")


def format_reference_entry(ref: ProjectReference, number: int) -> str:
    parts: list[str] = [f"[{number}]"]
    if (ref.authors or "").strip():
        parts.append(ref.authors.strip().rstrip("。.") + ".")
    if (ref.title or "").strip():
        parts.append(ref.title.strip().rstrip("。.") + ".")
    tail: list[str] = []
    if (ref.source or "").strip():
        tail.append(ref.source.strip().rstrip("，,。."))
    if (ref.year or "").strip():
        tail.append(str(ref.year).strip().rstrip("。."))
    if tail:
        parts.append(", ".join(tail) + ".")
    if (ref.extra or "").strip():
        parts.append(ref.extra.strip())
    return " ".join(parts)


def apply_citation_numbers(
    texts: Iterable[str],
    refs_by_id: dict[str, ProjectReference],
) -> tuple[list[str], list[tuple[int, ProjectReference]]]:
    index: dict[str, int] = {}
    order: list[str] = []

    def replacer(match: re.Match[str]) -> str:
        numbers: list[str] = []
        for raw_id in match.group(1).split(","):
            ref_id = raw_id.strip()
            if not ref_id or ref_id not in refs_by_id:
                continue
            if ref_id in index:
                continue
            order.append(ref_id)
            index[ref_id] = len(order)
            numbers.append(str(index[ref_id]))
        if not numbers:
            has_known_duplicate = any(
                raw_id.strip() in index for raw_id in match.group(1).split(",")
            )
            return "" if has_known_duplicate else match.group(0)
        return "[" + ",".join(numbers) + "]"

    remapped = [CITE_RE.sub(replacer, text or "") for text in texts]
    bibliography = [(index[ref_id], refs_by_id[ref_id]) for ref_id in order]
    return remapped, bibliography


def numbered_chapter_bodies(
    chapters: list,
    drafts: dict,
    references: list[ProjectReference] | None,
) -> tuple[dict[str, str], list[tuple[int, ProjectReference]]]:
    from app.export.common import chapters_by_id, covered_by_ancestor_draft, draft_body

    by_id = chapters_by_id(chapters)
    ordered: list[tuple[str, str]] = []
    for chapter in chapters:
        if is_bibliography_chapter(chapter.title) or covered_by_ancestor_draft(chapter, by_id, drafts):
            continue
        draft = drafts.get(chapter.id)
        if not draft:
            continue
        content = draft_body(chapter, draft)
        if content:
            ordered.append((chapter.id, content))
    refs_by_id = {item.id: item for item in references or []}
    remapped, bibliography = apply_citation_numbers(
        [content for _, content in ordered],
        refs_by_id,
    )
    bodies = {chapter_id: text for (chapter_id, _), text in zip(ordered, remapped)}
    return bodies, bibliography
