import re

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def normalize_heading_title(title: str) -> str:
    title = re.sub(r"^#+\s*", "", title)
    title = re.sub(r"^第[一二三四五六七八九十百千零〇\d]+[章节部分篇]\s*", "", title)
    title = re.sub(r"^(?:\d+(?:[.\-．]\d+)*)[、.．]?\s*", "", title)
    title = re.sub(r"^[（(][\d一二三四五六七八九十]+[）)]\s*", "", title)
    title = re.sub(r"[\s：:]+", "", title)
    return title.lower()


def titles_match(left: str, right: str) -> bool:
    a = normalize_heading_title(left)
    b = normalize_heading_title(right)
    return bool(a and b and a == b)


def find_markdown_sections(markdown: str) -> list[dict]:
    matches = [
        {"level": len(match.group(1)), "title": match.group(2).strip(), "start": match.start()}
        for match in HEADING_RE.finditer(markdown)
    ]
    sections = []
    for index, item in enumerate(matches):
        next_section = next(
            (other for other in matches[index + 1 :] if other["level"] <= item["level"]),
            None,
        )
        sections.append({**item, "end": next_section["start"] if next_section else len(markdown)})
    return sections


def extract_markdown_section(markdown: str, title: str, level: int | None = None) -> str | None:
    matches = [
        section
        for section in find_markdown_sections(markdown)
        if titles_match(section["title"], title)
    ]
    if not matches:
        return None
    section = next((item for item in matches if level is None or item["level"] == level), matches[0])
    return markdown[section["start"] : section["end"]].strip()
