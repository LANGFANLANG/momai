from sqlalchemy import func, select

from app.db.models import (
    ChapterDraft,
    ChapterRelation,
    ChapterSummary,
    ConsistencyIssue,
    Project,
    ProjectBrief,
    ProjectContext,
)
from app.ai.llm import LlmClient, MockLlmClient
from app.services.generation import GenerationService


class ScriptedLlmClient(LlmClient):
    def __init__(self, json_responses: list[dict], markdown_response: str):
        self.json_responses = iter(json_responses)
        self.markdown_response = markdown_response

    def complete_json(self, prompt: str) -> dict:
        return next(self.json_responses)

    def complete_markdown(self, prompt: str) -> str:
        return self.markdown_response


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
    assert chapters[0].title == "LLM Chapter"
    child = db_session.scalar(select(type(chapters[0])).where(type(chapters[0]).title == "LLM Section"))
    assert child is not None
    assert child.parent_id == chapters[0].id
    assert relations[0].next_bridge == "LLM next"
    assert draft.content == "# LLM Chapter\n\nLLM draft"
    assert summary.summary == "LLM summary"
    assert issues[0].type == "LLM issue"
