from dataclasses import dataclass
import re


TABLE_CAPTION_RE = re.compile(
    r"^表(?:题)?(?:\s*\d+(?:[.-]\d+)?)?\s*[:：]?\s*(.+)$"
)
TABLE_SEP_RE = re.compile(r"^\|?[\s:|-]+\|?$")
TAG_RE = re.compile(r"\\tag\s*\{[^}]*\}")

_CN_DIGITS = "零一二三四五六七八九"


@dataclass
class AcademicCounters:
    chapter_no: int = 0
    table_no: int = 0
    formula_no: int = 0


def to_chinese_num(n: int) -> str:
    if n <= 0:
        return str(n)
    if n < 10:
        return _CN_DIGITS[n]
    if n == 10:
        return "十"
    if n < 20:
        return "十" + _CN_DIGITS[n - 10]
    if n < 100:
        tens, ones = divmod(n, 10)
        return _CN_DIGITS[tens] + "十" + (_CN_DIGITS[ones] if ones else "")
    return str(n)


def formula_label(n: int) -> str:
    return f"（{to_chinese_num(n)}）"


def next_table_caption(counters: AcademicCounters, title: str) -> str:
    counters.table_no += 1
    chapter = counters.chapter_no or 1
    caption = f"表{chapter}.{counters.table_no}"
    title = title.strip()
    return f"{caption} {title}" if title else caption


def next_formula_label(counters: AcademicCounters) -> str:
    counters.formula_no += 1
    return formula_label(counters.formula_no)


def is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and not TABLE_SEP_RE.fullmatch(stripped)


def is_table_separator(line: str) -> bool:
    return TABLE_SEP_RE.fullmatch(line.strip()) is not None


def is_table_caption(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("表") or stripped.startswith("|") or len(stripped) > 80:
        return False
    return TABLE_CAPTION_RE.match(stripped) is not None


def caption_title(line: str) -> str:
    match = TABLE_CAPTION_RE.match(line.strip())
    if not match:
        return line.strip()
    title = match.group(1).strip()
    title = re.sub(r"^\d+(?:[.-]\d+)?\s*", "", title)
    return title.strip()


def parse_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def collect_table_rows(lines: list[str], start: int) -> tuple[int, list[list[str]]]:
    rows: list[list[str]] = []
    index = start
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            if rows:
                break
            index += 1
            continue
        if is_table_separator(stripped):
            index += 1
            continue
        if not stripped.startswith("|"):
            break
        rows.append(parse_table_row(stripped))
        index += 1
    return index, rows


def next_nonempty(lines: list[str], start: int) -> str | None:
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if stripped:
            return stripped
    return None


def strip_formula_tag(latex: str) -> str:
    return TAG_RE.sub("", latex).strip()
