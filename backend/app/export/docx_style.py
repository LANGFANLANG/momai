from pydantic import BaseModel

# 中文字号：小三 15 磅，四号 14 磅，小四 12 磅


class DocxStyle(BaseModel):
    heading_east_asia: str = "黑体"
    heading_ascii: str = "Times New Roman"
    body_east_asia: str = "宋体"
    body_ascii: str = "Times New Roman"
    heading1_size_pt: float = 15
    heading2_size_pt: float = 14
    heading3_size_pt: float = 12
    body_size_pt: float = 12
    first_line_indent_chars: float = 2
    space_before_pt: float = 0
    space_after_pt: float = 0
    line_spacing_multiple: float = 1.5


def resolve_docx_style(project, override: dict | None = None) -> DocxStyle:
    if override:
        return DocxStyle.model_validate(override)
    prefs = project.context.writing_prefs if project.context else None
    saved = prefs.get("export_docx") if isinstance(prefs, dict) else None
    if isinstance(saved, dict):
        return DocxStyle.model_validate(saved)
    return DocxStyle()
