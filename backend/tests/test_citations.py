from app.db.models import Chapter, ChapterDraft, Project, ProjectReference
from app.export.citations import (
    apply_citation_numbers,
    format_reference_entry,
    is_bibliography_chapter,
)
from app.export.markdown import build_markdown
from app.services.generation import GenerationService
from app.ai.llm import LlmClient, MockLlmClient


class RecordingMarkdownClient(LlmClient):
    def __init__(self, markdown: str = "# 绪论\n\n正文。"):
        self.prompt = ""
        self.markdown = markdown

    def complete_json(self, prompt: str) -> dict:
        raise AssertionError("Draft should not request JSON")

    def complete_markdown(self, prompt: str) -> str:
        self.prompt = prompt
        return self.markdown


def test_is_bibliography_chapter():
    assert is_bibliography_chapter("参考文献")
    assert is_bibliography_chapter("第8章 参考文献")
    assert is_bibliography_chapter("References")
    assert not is_bibliography_chapter("系统设计")


def test_citation_numbers_follow_first_appearance_not_list_order():
    first_added = ProjectReference(id="id-a", title="先录入的文献", authors="甲", year="2019")
    cited_first = ProjectReference(id="id-b", title="后录入但先引用", authors="乙", year="2021")
    texts, bibliography = apply_citation_numbers(
        [
            "Hive 适合大规模分析[cite:id-b]。",
            "对比方案见[cite:id-a,id-b]。",
        ],
        {"id-a": first_added, "id-b": cited_first},
    )
    assert texts[0] == "Hive 适合大规模分析[1]。"
    assert texts[1] == "对比方案见[2]。"
    assert [item.id for _, item in bibliography] == ["id-b", "id-a"]
    assert format_reference_entry(cited_first, 1).startswith("[1] 乙. 后录入但先引用.")


def test_unknown_citation_marker_is_kept():
    texts, bibliography = apply_citation_numbers(["未见[cite:missing]。"], {})
    assert texts == ["未见[cite:missing]。"]
    assert bibliography == []


def test_duplicate_citations_are_only_numbered_once():
    ref = ProjectReference(id="id-a", title="Hive 实践", authors="甲", year="2021")
    texts, bibliography = apply_citation_numbers(
        [
            "首次引用[cite:id-a]。",
            "后文再次提到同一文献[cite:id-a]。",
            "同一处混合新旧引用[cite:id-a,missing]。",
        ],
        {"id-a": ref},
    )
    assert texts == [
        "首次引用[1]。",
        "后文再次提到同一文献。",
        "同一处混合新旧引用。",
    ]
    assert [item.id for _, item in bibliography] == ["id-a"]


def test_markdown_export_numbers_citations_and_appends_bibliography():
    project = Project(type="thesis", title="Hive 电商数仓", language="zh")
    intro = Chapter(project=project, title="绪论", level=1, order=1)
    intro.id = "ch-intro"
    design = Chapter(project=project, title="系统设计", level=1, order=2)
    design.id = "ch-design"
    bib = Chapter(project=project, title="参考文献", level=1, order=3)
    bib.id = "ch-bib"
    older = ProjectReference(
        id="ref-old",
        project=project,
        authors="甲",
        title="先录入",
        source="计算机应用",
        year="2019",
        sort_order=1,
    )
    newer = ProjectReference(
        id="ref-new",
        project=project,
        authors="乙",
        title="后录入但先引用",
        source="软件学报",
        year="2021",
        sort_order=2,
    )
    intro_draft = ChapterDraft(
        chapter=intro,
        version=1,
        content="# 绪论\n\nHive 适合数据仓库[cite:ref-new]。",
        generation_mode="generate",
    )
    design_draft = ChapterDraft(
        chapter=design,
        version=1,
        content="# 系统设计\n\n分层设计参考[cite:ref-old]。",
        generation_mode="generate",
    )
    bib_draft = ChapterDraft(
        chapter=bib,
        version=1,
        content="# 参考文献\n\n请忽略这段草稿。",
        generation_mode="generate",
    )

    markdown = build_markdown(
        project,
        [intro, design, bib],
        {intro.id: intro_draft, design.id: design_draft, bib.id: bib_draft},
        references=[older, newer],
    )

    assert "Hive 适合数据仓库[1]。" in markdown
    assert "分层设计参考[2]。" in markdown
    assert markdown.index("[1]") < markdown.index("[2]")
    assert "# 参考文献" in markdown
    assert markdown.index("系统设计") < markdown.index("# 参考文献")
    assert "[1] 乙. 后录入但先引用. 软件学报, 2021." in markdown
    assert "[2] 甲. 先录入. 计算机应用, 2019." in markdown
    assert "请忽略这段草稿" not in markdown


def test_generate_draft_uses_user_references_and_skips_bibliography_chapter(db_session):
    project = Project(type="thesis", title="Cite Hive", language="zh")
    intro = Chapter(project=project, title="绪论", level=1, order=1)
    bib = Chapter(project=project, title="参考文献", level=1, order=2)
    ref = ProjectReference(
        project=project,
        authors="乙",
        title="Hive 实践",
        source="软件学报",
        year="2021",
        sort_order=1,
    )
    db_session.add_all([project, intro, bib, ref])
    db_session.commit()
    client = RecordingMarkdownClient("# 绪论\n\n引用[cite:x]。")

    draft = GenerationService.generate_draft(db_session, intro.id, "generate", client=client)

    assert f"[cite:{ref.id}]" in client.prompt
    assert "Hive 实践" in client.prompt
    assert draft.content.startswith("# 绪论")

    placeholder = GenerationService.generate_draft(
        db_session, bib.id, "generate", client=MockLlmClient()
    )
    assert "首次引用的顺序" in placeholder.content
    assert placeholder.prompt_snapshot == {"placeholder": True}
