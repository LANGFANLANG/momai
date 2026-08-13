import pytest
from sqlalchemy import func, select

from app.db.models import (
    Chapter,
    ChapterDraft,
    ChapterRelation,
    ChapterSummary,
    ConsistencyIssue,
    Project,
    ProjectBrief,
    ProjectContext,
)
from app.ai.llm import LlmClient, MockLlmClient
from app.services.generation import (
    ConsistencyFixConflict,
    GenerationService,
    OutlineRegenerationConflict,
)


class ScriptedLlmClient(LlmClient):
    def __init__(self, json_responses: list[dict], markdown_response: str):
        self.json_responses = iter(json_responses)
        self.markdown_response = markdown_response

    def complete_json(self, prompt: str) -> dict:
        return next(self.json_responses)

    def complete_markdown(self, prompt: str) -> str:
        return self.markdown_response


class RecordingJsonClient(LlmClient):
    def __init__(self, payload: dict):
        self.prompt = ""
        self.payload = payload

    def complete_json(self, prompt: str) -> dict:
        self.prompt = prompt
        return self.payload

    def complete_markdown(self, prompt: str) -> str:
        raise AssertionError("Relations should not request Markdown")


class ReviewPromptClient(LlmClient):
    def __init__(self):
        self.prompt = ""

    def complete_json(self, prompt: str) -> dict:
        self.prompt = prompt
        return {"issues": []}

    def complete_markdown(self, prompt: str) -> str:
        raise AssertionError("Review should not request Markdown")


def test_mock_generation_flow_persists_each_stage(db_session):
    client = MockLlmClient()
    project = Project(type="thesis", title="LifePilot", language="zh")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        ProjectContext(
            project_id=project.id,
            background="面向学生的学习规划系统研究。",
            goal="设计学习规划系统。",
            modules=["学习计划", "进度跟踪"],
        )
    )
    db_session.commit()

    brief = GenerationService.generate_brief(db_session, project.id, client)

    assert brief.background == "面向学生的学习规划系统研究。"
    assert db_session.get(ProjectBrief, brief.id) is not None

    chapters = GenerationService.generate_outline(
        db_session, project.id, "engineering_focused", client
    )

    assert [chapter.title for chapter in chapters] == [
        "绪论",
        "相关理论与技术基础",
        "需求分析",
        "系统设计",
        "系统实现",
        "测试与结果分析",
        "总结与展望",
        "参考文献",
    ]
    assert db_session.scalar(select(func.count()).select_from(type(chapters[0]))) == 8

    relations = GenerationService.generate_relations(db_session, project.id, client)

    assert len(relations) == len(chapters)
    assert db_session.scalar(select(func.count()).select_from(ChapterRelation)) == len(chapters)

    draft = GenerationService.generate_draft(
        db_session, chapters[0].id, "generate", "突出研究背景", client
    )

    assert draft.content.startswith("# 绪论")
    assert db_session.get(ChapterDraft, draft.id) is not None

    summary = GenerationService.generate_summary(db_session, chapters[0].id, client)

    assert summary.summary == "绪论概述了本章的核心内容。"
    assert db_session.get(ChapterSummary, summary.id) is not None

    issues = GenerationService.review_consistency(db_session, project.id, client)

    assert issues[0].type == "structure_review"
    assert db_session.scalar(select(func.count()).select_from(ConsistencyIssue)) == len(issues)


def test_structured_llm_output_is_persisted(db_session):
    project = Project(type="thesis", title="Structured Flow", language="zh")
    db_session.add(project)
    db_session.commit()
    client = ScriptedLlmClient(
        [
            {
                "background": "LLM background",
                "core_problem": "LLM problem",
                "goal": "LLM goal",
            },
            {
                "chapters": [
                    {
                        "title": "LLM Chapter",
                        "level": 1,
                        "order": 1,
                        "purpose": "LLM purpose",
                        "suggested_word_count": 1000,
                        "children": [
                            {
                                "title": "LLM Section",
                                "level": 2,
                                "order": 1,
                                "purpose": "LLM section purpose",
                                "suggested_word_count": 500,
                            }
                        ],
                    }
                ]
            },
            {
                "relations": [
                    {
                        "chapter_title": "LLM Chapter",
                        "previous_bridge": "LLM previous",
                        "next_bridge": "LLM next",
                    }
                ]
            },
            {"summary": "LLM summary"},
            {
                "issues": [
                    {
                        "severity": "high",
                        "type": "LLM issue",
                        "chapter_title": "LLM Chapter",
                        "description": "LLM description",
                    }
                ]
            },
        ],
        "# LLM Chapter\n\nLLM draft",
    )

    brief = GenerationService.generate_brief(db_session, project.id, client)
    chapters = GenerationService.generate_outline(db_session, project.id, "custom", client)
    relations = GenerationService.generate_relations(db_session, project.id, client)
    draft = GenerationService.generate_draft(db_session, chapters[0].id, "generate", client=client)
    summary = GenerationService.generate_summary(db_session, chapters[0].id, client)
    issues = GenerationService.review_consistency(db_session, project.id, client)

    assert brief.background == "LLM background"
    assert [chapter.title for chapter in chapters] == ["LLM Chapter", "LLM Section"]
    child = chapters[1]
    assert child.parent_id == chapters[0].id
    assert relations[0].next_bridge == "LLM next"
    assert draft.content == "# LLM Chapter\n\nLLM draft"
    assert summary.summary == "LLM summary"
    assert issues[0].type == "LLM issue"


@pytest.mark.parametrize("downstream", ["relation", "draft", "summary"])
def test_outline_regeneration_rejects_when_downstream_work_exists(db_session, downstream):
    project = Project(type="thesis", title="Protected work", language="zh")
    chapter = Chapter(project=project, title="Existing chapter", level=1, order=1)
    db_session.add(project)
    db_session.flush()
    if downstream == "relation":
        db_session.add(ChapterRelation(chapter=chapter, key_points=["keep relation"]))
    elif downstream == "draft":
        db_session.add(
            ChapterDraft(
                chapter=chapter,
                version=1,
                content="keep draft",
                generation_mode="generate",
            )
        )
    else:
        db_session.add(ChapterSummary(chapter=chapter, summary="keep summary"))
    db_session.commit()

    with pytest.raises(OutlineRegenerationConflict):
        GenerationService.generate_outline(db_session, project.id, client=MockLlmClient())

    assert db_session.get(Chapter, chapter.id) is not None
    assert db_session.scalar(select(func.count()).select_from(Chapter)) == 1


def test_outline_regeneration_force_replaces_downstream_work(db_session):
    project = Project(type="thesis", title="Replace work", language="zh")
    chapter = Chapter(project=project, title="Existing chapter", level=1, order=1)
    db_session.add_all(
        [
            project,
            ChapterDraft(
                chapter=chapter,
                version=1,
                content="replace me",
                generation_mode="generate",
            ),
        ]
    )
    db_session.commit()

    chapters = GenerationService.generate_outline(
        db_session, project.id, force=True, client=MockLlmClient()
    )

    assert chapters[0].title == "绪论"
    assert db_session.get(Chapter, chapter.id) is None


def test_generate_relations_prompt_includes_outline_titles(db_session):
    project = Project(type="thesis", title="LifePilot", language="zh")
    db_session.add_all(
        [
            project,
            ProjectBrief(
                project=project,
                background="面向学生的学习规划系统研究。",
                goal="设计学习规划系统。",
            ),
            Chapter(
                project=project,
                title="绪论",
                level=1,
                order=1,
                purpose="交代研究背景。",
            ),
        ]
    )
    db_session.commit()
    client = RecordingJsonClient(
        {
            "relations": [
                {
                    "chapter_title": "绪论",
                    "previous_bridge": "从研究背景切入。",
                    "next_bridge": "引出相关理论。",
                }
            ]
        }
    )

    GenerationService.generate_relations(db_session, project.id, client)

    assert "绪论" in client.prompt
    assert "交代研究背景。" in client.prompt
    assert "面向学生的学习规划系统研究。" in client.prompt
    assert "Chapter object" not in client.prompt
    assert "ProjectBrief object" not in client.prompt


def test_generate_brief_accepts_nested_project_brief_payload(db_session):
    project = Project(type="thesis", title="LifePilot", language="zh")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        ProjectContext(
            project_id=project.id,
            background="面向学生的学习规划系统研究。",
            goal="设计学习规划系统。",
        )
    )
    db_session.commit()
    client = ScriptedLlmClient(
        [
            {
                "project_brief": {
                    "title_explanation": "LifePilot",
                    "background": "面向学生的学习规划系统研究。",
                    "core_problem": "学习规划缺少系统支持。",
                    "goal": "设计学习规划系统。",
                    "significance": "提升学习规划效率。",
                    "technical_route": "按需求、设计、实现与测试推进。",
                    "modules": ["学习计划"],
                    "expected_result": "形成项目报告初稿。",
                    "writing_boundary": "仅基于用户提供的项目事实写作。",
                    "missing_info": ["格式与字数要求"],
                    "locked_facts": ["LifePilot"],
                }
            }
        ],
        "",
    )

    brief = GenerationService.generate_brief(db_session, project.id, client)

    assert brief.background == "面向学生的学习规划系统研究。"
    assert brief.missing_info == ["格式与字数要求"]


def test_consistency_review_uses_only_latest_draft_per_chapter(db_session):
    project = Project(type="thesis", title="Latest review", language="zh")
    chapter = Chapter(project=project, title="Chapter", level=1, order=1)
    db_session.add_all(
        [
            project,
            ChapterDraft(
                chapter=chapter,
                version=1,
                content="STALE_DRAFT_CONTENT",
                generation_mode="generate",
            ),
            ChapterDraft(
                chapter=chapter,
                version=2,
                content="LATEST_DRAFT_CONTENT",
                generation_mode="rewrite",
            ),
        ]
    )
    db_session.commit()
    client = ReviewPromptClient()

    GenerationService.review_consistency(db_session, project.id, client)

    assert "LATEST_DRAFT_CONTENT" in client.prompt
    assert "STALE_DRAFT_CONTENT" not in client.prompt


def test_parent_draft_marks_matched_child_status_drafted(db_session):
    project = Project(type="thesis", title="Hive", language="zh")
    parent = Chapter(project=project, title="绪论", level=1, order=1, status="relation_ready")
    matched = Chapter(
        project=project,
        parent=parent,
        title="项目背景与意义",
        level=2,
        order=1,
        status="planned",
    )
    unmatched = Chapter(
        project=project,
        parent=parent,
        title="未出现的小节",
        level=2,
        order=2,
        status="planned",
    )
    db_session.add_all([project, parent, matched, unmatched])
    db_session.commit()
    client = ScriptedLlmClient(
        [],
        "# 第1章 绪论\n\n引言。\n\n## 1.1 项目背景与意义\n\n背景段落。\n",
    )

    GenerationService.generate_draft(db_session, parent.id, "generate", client=client)

    db_session.refresh(parent)
    db_session.refresh(matched)
    db_session.refresh(unmatched)
    assert parent.status == "drafted"
    assert matched.status == "drafted"
    assert unmatched.status == "planned"


def test_sync_matched_child_statuses_from_existing_parent_draft(db_session):
    project = Project(type="thesis", title="Hive", language="zh")
    parent = Chapter(project=project, title="绪论", level=1, order=1, status="drafted")
    child = Chapter(
        project=project,
        parent=parent,
        title="国内外研究现状",
        level=2,
        order=1,
        status="planned",
    )
    db_session.add_all(
        [
            project,
            parent,
            child,
            ChapterDraft(
                chapter=parent,
                version=1,
                content="# 第1章 绪论\n\n## 1.2 国内外研究现状\n\n现状。\n",
                generation_mode="generate",
            ),
        ]
    )
    db_session.commit()

    GenerationService.sync_matched_child_draft_statuses(db_session, project.id)

    db_session.refresh(child)
    assert child.status == "drafted"


class FixPromptClient(LlmClient):
    def __init__(self, payload: dict, markdown: str):
        self.prompt = ""
        self.markdown_prompt = ""
        self.payload = payload
        self.markdown = markdown

    def complete_json(self, prompt: str) -> dict:
        self.prompt = prompt
        return self.payload

    def complete_markdown(self, prompt: str) -> str:
        self.markdown_prompt = prompt
        return self.markdown


def _project_with_draft(db_session, title="Chapter", content="original draft"):
    project = Project(type="thesis", title="Fixable", language="zh")
    chapter = Chapter(project=project, title=title, level=1, order=1, status="drafted")
    draft = ChapterDraft(
        chapter=chapter,
        version=1,
        content=content,
        generation_mode="generate",
    )
    db_session.add_all([project, chapter, draft])
    db_session.commit()
    return project, chapter, draft


def test_fix_consistency_issue_writes_new_draft_and_marks_fixed(db_session):
    project, chapter, draft = _project_with_draft(db_session, content="ODS stores raw data.")
    issue = ConsistencyIssue(
        project_id=project.id,
        chapter_id=chapter.id,
        severity="high",
        type="definition_consistency",
        description="ODS definition is inconsistent.",
        suggestion="Clarify that ODS stores raw data without cleaning.",
    )
    db_session.add(issue)
    db_session.commit()
    client = FixPromptClient(
        {
            "chapter_updates": [{"chapter_title": chapter.title}],
            "fix_summary": "Aligned the ODS definition.",
        },
        "ODS stores raw data without cleaning.",
    )

    updated_issue, drafts, summary = GenerationService.fix_consistency_issue(
        db_session, project.id, issue.id, client
    )

    assert updated_issue.status == "fixed"
    assert summary == "Aligned the ODS definition."
    assert "Clarify that ODS stores raw data without cleaning." in client.prompt
    assert "ODS definition is inconsistent." in client.prompt
    assert "ODS stores raw data." in client.markdown_prompt
    assert drafts[0].content == "ODS stores raw data without cleaning."
    assert drafts[0].version == 2
    assert drafts[0].generation_mode == "rewrite"
    assert db_session.get(ChapterDraft, draft.id).content == "ODS stores raw data."


def test_fix_consistency_issue_matches_normalized_chapter_title(db_session):
    project, chapter, _ = _project_with_draft(db_session, title="系统设计", content="old")
    issue = ConsistencyIssue(
        project_id=project.id,
        severity="medium",
        type="tool_consistency",
        description="Tool names differ.",
        suggestion="Use DataX throughout.",
    )
    db_session.add(issue)
    db_session.commit()
    client = FixPromptClient(
        {"chapter_updates": [{"chapter_title": "第4章 系统设计"}]},
        "Use DataX only.",
    )

    _, drafts, _ = GenerationService.fix_consistency_issue(
        db_session, project.id, issue.id, client
    )

    assert drafts[0].chapter_id == chapter.id
    assert drafts[0].content == "Use DataX only."


def test_fix_consistency_issue_rejects_closed_issue(db_session):
    project, chapter, _ = _project_with_draft(db_session)
    issue = ConsistencyIssue(
        project_id=project.id,
        chapter_id=chapter.id,
        severity="low",
        type="completeness",
        description="Placeholder remains.",
        status="ignored",
    )
    db_session.add(issue)
    db_session.commit()

    with pytest.raises(ConsistencyFixConflict, match="Only open"):
        GenerationService.fix_consistency_issue(
            db_session, project.id, issue.id, MockLlmClient()
        )


def test_mock_fix_appends_revision_note_to_linked_chapter(db_session):
    project, chapter, _ = _project_with_draft(db_session, content="chapter body")
    issue = ConsistencyIssue(
        project_id=project.id,
        chapter_id=chapter.id,
        severity="low",
        type="structure_review",
        description="Check structure.",
        suggestion="Add a transition.",
    )
    db_session.add(issue)
    db_session.commit()

    updated_issue, drafts, summary = GenerationService.fix_consistency_issue(
        db_session, project.id, issue.id, MockLlmClient()
    )

    assert updated_issue.status == "fixed"
    assert drafts[0].content.endswith("已按一致性建议修订。")
    assert summary == "已根据建议修订相关章节。"


def test_fix_consistency_issue_rewrites_parent_draft_for_child_title(db_session):
    project = Project(type="thesis", title="Hive", language="zh")
    parent = Chapter(project=project, title="数据仓库建设与分析", level=1, order=1, status="drafted")
    child = Chapter(
        project=project,
        parent=parent,
        title="Hive环境搭建",
        level=2,
        order=1,
        status="drafted",
    )
    db_session.add_all(
        [
            project,
            parent,
            child,
            ChapterDraft(
                chapter=parent,
                version=1,
                content="# 数据仓库建设与分析\n\n## Hive环境搭建\n\n环境未介绍。\n",
                generation_mode="generate",
            ),
        ]
    )
    db_session.commit()
    issue = ConsistencyIssue(
        project_id=project.id,
        chapter_id=child.id,
        severity="high",
        type="structure_order",
        description="环境搭建顺序不对。",
        suggestion="先介绍 Hive 环境再建表。",
    )
    db_session.add(issue)
    db_session.commit()
    rewritten = "# 数据仓库建设与分析\n\n## Hive环境搭建\n\n先介绍环境再建表。"
    client = FixPromptClient(
        {"chapter_updates": [{"chapter_title": "Hive环境搭建"}]},
        rewritten,
    )

    _, drafts, _ = GenerationService.fix_consistency_issue(
        db_session, project.id, issue.id, client
    )

    assert drafts[0].chapter_id == parent.id
    assert drafts[0].content == rewritten
    assert drafts[0].version == 2
    assert "Hive环境搭建" in client.markdown_prompt
    assert "环境未介绍" in client.markdown_prompt
    assert "先介绍 Hive 环境再建表" in client.markdown_prompt
