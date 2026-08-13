from app.services.markdown_sections import extract_markdown_section, titles_match


def test_titles_match_ignores_chapter_numbering():
    assert titles_match("第1章 绪论", "绪论")
    assert titles_match("1.1 项目背景与意义", "项目背景与意义")
    assert not titles_match("项目背景与意义", "国内外研究现状")


def test_extract_markdown_section_by_child_title():
    markdown = """# 第1章 绪论

引言。

## 1.1 项目背景与意义

背景段落。

## 1.2 国内外研究现状

现状段落。
"""

    section = extract_markdown_section(markdown, "项目背景与意义", 2)

    assert section is not None
    assert section.startswith("## 1.1 项目背景与意义")
    assert "背景段落。" in section
    assert "国内外研究现状" not in section
