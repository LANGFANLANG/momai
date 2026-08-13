import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from app.db.models import Chapter, ChapterDraft, PaperAbstract, Project
from app.export.common import (
    abstract_has_content,
    chapters_by_id,
    covered_by_ancestor_draft,
    draft_body,
    join_keywords,
)
from app.export.docx_style import DocxStyle

HEADING_RE = re.compile(r"^(#{1,6})\s*(.+?)\s*#*\s*$")
UL_RE = re.compile(r"^[-*+]\s+(.+)$")
OL_RE = re.compile(r"^\d+[.)、]\s+(.+)$")
HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
INLINE_RE = re.compile(
    r"!\[[^\]]*\]\([^)]*\)|"
    r"\[([^\]]+)\]\([^)]*\)|"
    r"\*\*(.+?)\*\*|"
    r"__(.+?)__|"
    r"`([^`]+)`|"
    r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|"
    r"~~(.+?)~~"
)
THEME_FONT_ATTRS = (
    qn("w:asciiTheme"),
    qn("w:hAnsiTheme"),
    qn("w:eastAsiaTheme"),
    qn("w:cstheme"),
)
THEME_COLOR_ATTRS = (qn("w:themeColor"), qn("w:themeTint"), qn("w:themeShade"))


def _apply_rpr(r_pr, ascii_font: str, east_asia: str, size_pt: float, bold: bool) -> None:
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)
    r_fonts.set(qn("w:ascii"), ascii_font)
    r_fonts.set(qn("w:hAnsi"), ascii_font)
    r_fonts.set(qn("w:eastAsia"), east_asia)
    r_fonts.set(qn("w:cs"), ascii_font)
    for attr in THEME_FONT_ATTRS:
        if attr in r_fonts.attrib:
            del r_fonts.attrib[attr]

    half_points = str(int(round(size_pt * 2)))
    for tag in ("w:sz", "w:szCs"):
        element = r_pr.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            r_pr.append(element)
        element.set(qn("w:val"), half_points)

    for tag, enabled in (("w:b", bold), ("w:bCs", bold)):
        element = r_pr.find(qn(tag))
        if enabled:
            if element is None:
                element = OxmlElement(tag)
                r_pr.append(element)
            element.set(qn("w:val"), "true")
        elif element is not None:
            r_pr.remove(element)

    for tag in ("w:i", "w:iCs"):
        element = r_pr.find(qn(tag))
        if element is not None:
            r_pr.remove(element)

    color = r_pr.find(qn("w:color"))
    if color is None:
        color = OxmlElement("w:color")
        r_pr.append(color)
    color.set(qn("w:val"), "000000")
    for attr in THEME_COLOR_ATTRS:
        if attr in color.attrib:
            del color.attrib[attr]


def _set_run_font(run, ascii_font: str, east_asia: str, size_pt: float, bold: bool = False) -> None:
    _apply_rpr(run._element.get_or_add_rPr(), ascii_font, east_asia, size_pt, bold)


def _set_style_font(style_obj, ascii_font: str, east_asia: str, size_pt: float, bold: bool) -> None:
    _apply_rpr(style_obj.element.get_or_add_rPr(), ascii_font, east_asia, size_pt, bold)


def _apply_paragraph_spacing(paragraph, style: DocxStyle, *, indent_pt: float | None = None) -> None:
    fmt = paragraph.paragraph_format
    fmt.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    fmt.line_spacing = style.line_spacing_multiple
    fmt.space_before = Pt(style.space_before_pt)
    fmt.space_after = Pt(style.space_after_pt)
    fmt.first_line_indent = Pt(0) if indent_pt is None else Pt(indent_pt)


def _configure_page(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)


def _configure_styles(document: Document, style: DocxStyle) -> None:
    normal = document.styles["Normal"]
    _set_style_font(normal, style.body_ascii, style.body_east_asia, style.body_size_pt, False)
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    normal.paragraph_format.line_spacing = style.line_spacing_multiple
    normal.paragraph_format.space_before = Pt(style.space_before_pt)
    normal.paragraph_format.space_after = Pt(style.space_after_pt)
    normal.paragraph_format.first_line_indent = Pt(style.body_size_pt * style.first_line_indent_chars)
    for level in range(1, 7):
        heading = document.styles[f"Heading {level}"]
        _set_style_font(
            heading,
            style.heading_ascii,
            style.heading_east_asia,
            _heading_size(style, level),
            True,
        )
        heading.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        heading.paragraph_format.line_spacing = style.line_spacing_multiple
        heading.paragraph_format.space_before = Pt(style.space_before_pt)
        heading.paragraph_format.space_after = Pt(style.space_after_pt)
        heading.paragraph_format.first_line_indent = Pt(0)


def _heading_size(style: DocxStyle, level: int) -> float:
    if level <= 1:
        return style.heading1_size_pt
    if level == 2:
        return style.heading2_size_pt
    return style.heading3_size_pt


def _clean_residual(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return text.replace("**", "").replace("__", "").replace("`", "")


def _inline_chunks(text: str):
    text = re.sub(r"<!--.*?-->", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    pos = 0
    for match in INLINE_RE.finditer(text):
        if match.start() > pos:
            yield _clean_residual(text[pos : match.start()]), False
        if match.group(0).startswith("!["):
            alt = re.match(r"!\[([^\]]*)\]", match.group(0))
            yield (alt.group(1) if alt else ""), False
        elif match.group(1):
            yield match.group(1), False
        elif match.group(2) or match.group(3):
            yield match.group(2) or match.group(3), True
        else:
            yield match.group(4) or match.group(5) or match.group(6) or "", False
        pos = match.end()
    if pos < len(text) or pos == 0:
        yield _clean_residual(text[pos:]), False


def _plain_text(text: str) -> str:
    return "".join(chunk for chunk, _ in _inline_chunks(text))


def _add_inline_runs(paragraph, text: str, ascii_font: str, east_asia: str, size_pt: float, *, base_bold: bool) -> None:
    emitted = False
    for chunk, make_bold in _inline_chunks(text):
        if not chunk:
            continue
        run = paragraph.add_run(chunk)
        _set_run_font(run, ascii_font, east_asia, size_pt, base_bold or make_bold)
        emitted = True
    if not emitted:
        run = paragraph.add_run("")
        _set_run_font(run, ascii_font, east_asia, size_pt, base_bold)


def _add_title(document: Document, text: str, style: DocxStyle) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _apply_paragraph_spacing(paragraph, style)
    _add_inline_runs(
        paragraph,
        text,
        style.heading_ascii,
        style.heading_east_asia,
        style.heading1_size_pt,
        base_bold=True,
    )


def _add_heading(document: Document, text: str, level: int, style: DocxStyle) -> None:
    style_level = min(max(level, 1), 6)
    paragraph = document.add_paragraph()
    paragraph.style = document.styles[f"Heading {style_level}"]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    _apply_paragraph_spacing(paragraph, style)
    _add_inline_runs(
        paragraph,
        _plain_text(text),
        style.heading_ascii,
        style.heading_east_asia,
        _heading_size(style, level),
        base_bold=True,
    )


def _add_body(document: Document, text: str, style: DocxStyle, *, indent: bool = True) -> None:
    paragraph = document.add_paragraph()
    paragraph.style = document.styles["Normal"]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    indent_pt = style.body_size_pt * style.first_line_indent_chars if indent else 0
    _apply_paragraph_spacing(paragraph, style, indent_pt=indent_pt)
    _add_inline_runs(
        paragraph,
        text,
        style.body_ascii,
        style.body_east_asia,
        style.body_size_pt,
        base_bold=False,
    )


def _add_markdown(document: Document, markdown: str, style: DocxStyle) -> None:
    in_code = False
    for raw in markdown.splitlines():
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if not stripped or HR_RE.fullmatch(stripped):
            continue
        if stripped.startswith(">"):
            stripped = stripped.lstrip("> ").strip()
            if not stripped:
                continue
        if in_code:
            _add_body(document, stripped, style, indent=False)
            continue
        heading = HEADING_RE.match(stripped)
        if heading:
            _add_heading(document, heading.group(2).strip(), len(heading.group(1)), style)
            continue
        if stripped.startswith("|"):
            if re.fullmatch(r"\|?[\s:|-]+\|?", stripped):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            _add_body(document, "    ".join(_plain_text(cell) for cell in cells), style, indent=False)
            continue
        bullet = UL_RE.match(stripped)
        if bullet:
            _add_body(document, f"• {bullet.group(1).strip()}", style, indent=False)
            continue
        numbered = OL_RE.match(stripped)
        if numbered:
            _add_body(document, stripped, style, indent=False)
            continue
        _add_body(document, stripped, style)


def _add_centered(document: Document, text: str, style: DocxStyle, size_pt: float) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _apply_paragraph_spacing(paragraph, style)
    _add_inline_runs(
        paragraph,
        text,
        style.heading_ascii,
        style.heading_east_asia,
        size_pt,
        base_bold=True,
    )


def _add_abstracts(document: Document, abstract: PaperAbstract | None, style: DocxStyle) -> None:
    if not abstract_has_content(abstract) or abstract is None:
        return
    if (abstract.abstract_zh or "").strip():
        _add_heading(document, "摘要", 1, style)
        _add_markdown(document, abstract.abstract_zh, style)
        keywords = join_keywords(abstract.keywords_zh, chinese=True)
        if keywords:
            _add_body(document, f"**关键词：** {keywords}", style, indent=False)
    if (abstract.abstract_en or "").strip() or (abstract.title_en or "").strip():
        _add_heading(document, "Abstract", 1, style)
        if (abstract.title_en or "").strip():
            _add_centered(document, abstract.title_en.strip(), style, style.heading2_size_pt)
        if (abstract.abstract_en or "").strip():
            _add_markdown(document, abstract.abstract_en, style)
        keywords = join_keywords(abstract.keywords_en, chinese=False)
        if keywords:
            _add_body(document, f"**Keywords:** {keywords}", style, indent=False)


def build_docx(
    output_path: Path,
    project: Project,
    chapters: list[Chapter],
    drafts: dict[str, ChapterDraft],
    style: DocxStyle | None = None,
    paper_abstract: PaperAbstract | None = None,
) -> None:
    style = style or DocxStyle()
    document = Document()
    _configure_page(document)
    _configure_styles(document, style)
    _add_title(document, project.title, style)
    _add_abstracts(document, paper_abstract, style)
    by_id = chapters_by_id(chapters)
    for chapter in chapters:
        if covered_by_ancestor_draft(chapter, by_id, drafts):
            continue
        _add_heading(document, chapter.title, max(chapter.level, 1), style)
        draft = drafts.get(chapter.id)
        if draft:
            _add_markdown(document, draft_body(chapter, draft), style)
    document.save(output_path)
