from app.services.export import download_filename, sanitize_export_stem


def test_sanitize_export_stem_keeps_chinese_title():
    assert sanitize_export_stem("基于Hive的电商数据仓库设计与实现") == "基于Hive的电商数据仓库设计与实现"


def test_sanitize_export_stem_strips_illegal_characters():
    assert sanitize_export_stem('A/B:C*|?.docx') == "ABC.docx"
    assert sanitize_export_stem("  ...  ") == "export"


def test_download_filename_uses_project_title_and_suffix():
    assert download_filename("基于Hive的电商数据仓库设计与实现", ".docx") == (
        "基于Hive的电商数据仓库设计与实现.docx"
    )
    assert download_filename("Paper Agent", "md") == "Paper Agent.md"
