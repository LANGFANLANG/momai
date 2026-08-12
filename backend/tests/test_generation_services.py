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
from app.services.generation import GenerationService


def test_mock_generation_flow_persists_each_stage(db_session):
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

    brief = GenerationService.generate_brief(db_session, project.id)

    assert brief.background == "面向学生的学习规划系统研究。"
    assert db_session.get(ProjectBrief, brief.id) is not None

    chapters = GenerationService.generate_outline(db_session, project.id, "engineering_focused")

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

    relations = GenerationService.generate_relations(db_session, project.id)

    assert len(relations) == len(chapters)
    assert db_session.scalar(select(func.count()).select_from(ChapterRelation)) == len(chapters)

    draft = GenerationService.generate_draft(
        db_session, chapters[0].id, "generate", "突出研究背景"
    )

    assert draft.content.startswith("# 绪论")
    assert db_session.get(ChapterDraft, draft.id) is not None

    summary = GenerationService.generate_summary(db_session, chapters[0].id)

    assert summary.summary == "绪论概述了本章的核心内容。"
    assert db_session.get(ChapterSummary, summary.id) is not None

    issues = GenerationService.review_consistency(db_session, project.id)

    assert issues[0].type == "structure_review"
    assert db_session.scalar(select(func.count()).select_from(ConsistencyIssue)) == len(issues)
