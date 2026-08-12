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
from app.services.generation import GenerationService, OutlineRegenerationConflict


class ScriptedLlmClient(LlmClient):
    def __init__(self, json_responses: list[dict], markdown_response: str):
        self.json_responses = iter(json_responses)
        self.markdown_response = markdown_response

    def complete_json(self, prompt: str) -> dict:
        return next(self.json_responses)

    def complete_markdown(self, prompt: str) -> str:
        return self.markdown_response


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
