from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.llm import LlmClient, MockLlmClient, get_llm_client
from app.ai.prompts import (
    BRIEF_PROMPT,
    CHAPTER_DRAFT_PROMPT,
    CHAPTER_SUMMARY_PROMPT,
    CONSISTENCY_REVIEW_PROMPT,
    OUTLINE_PROMPT,
    RELATION_PROMPT,
)
from app.db.models import (
    Chapter,
    ChapterDraft,
    ChapterRelation,
    ChapterSummary,
    ConsistencyIssue,
    Project,
    ProjectBrief,
)
from app.services.projects import ProjectService


class GenerationService:
    @staticmethod
    def _client(client: LlmClient | None) -> LlmClient:
        return client or get_llm_client()

    @staticmethod
    def _commit_and_refresh(db: Session, row):
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @classmethod
    def generate_brief(
        cls, db: Session, project_id: str, client: LlmClient | None = None
    ) -> ProjectBrief:
        project = ProjectService.get_project_or_404(db, project_id)
        context = project.context
        prompt = BRIEF_PROMPT.format(
            project_type=project.type,
            project_title=project.title,
            project_context=context,
        )
        llm = cls._client(client)
        if not isinstance(llm, MockLlmClient):
            llm.complete(prompt)

        brief = project.brief or ProjectBrief(project_id=project.id)
        brief.title_explanation = project.title
        brief.background = (context.background if context else None) or "围绕项目主题整理研究背景。"
        brief.core_problem = (context.problem if context else None) or "明确项目需要解决的核心问题。"
        brief.goal = (context.goal if context else None) or "完成项目目标的分析与设计。"
        brief.significance = "说明项目的理论与实践意义。"
        brief.technical_route = (context.architecture if context else None) or "按照需求、设计、实现与测试推进。"
        brief.modules = (context.modules if context else None) or []
        brief.expected_result = "形成结构完整的项目报告初稿。"
        brief.writing_boundary = "仅基于用户提供的项目事实写作。"
        brief.missing_info = []
        brief.locked_facts = [project.title, *brief.modules]
        project.status = "brief_ready"
        return cls._commit_and_refresh(db, brief)

    @classmethod
    def generate_outline(
        cls,
        db: Session,
        project_id: str,
        outline_preference: str | None = None,
        client: LlmClient | None = None,
    ) -> list[Chapter]:
        project = ProjectService.get_project_or_404(db, project_id)
        prompt = OUTLINE_PROMPT.format(
            project_type=project.type,
            target_word_count=project.target_word_count,
            requirements=project.requirements,
            project_brief=project.brief,
        )
        llm = cls._client(client)
        if not isinstance(llm, MockLlmClient):
            llm.complete(prompt)

        for chapter in list(project.chapters):
            db.delete(chapter)
        db.flush()
        titles = [
            "绪论",
            "相关理论与技术基础",
            "需求分析",
            "系统设计",
            "系统实现",
            "测试与结果分析",
            "总结与展望",
            "参考文献",
        ]
        word_count = (project.target_word_count or 8000) // len(titles)
        chapters = [
            Chapter(
                project_id=project.id,
                title=title,
                level=1,
                order=index,
                purpose=f"完成{title}的论述。",
                suggested_word_count=word_count,
            )
            for index, title in enumerate(titles, start=1)
        ]
        db.add_all(chapters)
        project.status = "outline_ready"
        db.commit()
        for chapter in chapters:
            db.refresh(chapter)
        return chapters

    @classmethod
    def generate_relations(
        cls, db: Session, project_id: str, client: LlmClient | None = None
    ) -> list[ChapterRelation]:
        project = ProjectService.get_project_or_404(db, project_id)
        chapters = list(db.scalars(select(Chapter).where(Chapter.project_id == project.id).order_by(Chapter.order)))
        prompt = RELATION_PROMPT.format(project_brief=project.brief, outline=chapters)
        llm = cls._client(client)
        if not isinstance(llm, MockLlmClient):
            llm.complete(prompt)

        relations = []
        for index, chapter in enumerate(chapters):
            relation = chapter.relation or ChapterRelation(chapter_id=chapter.id)
            previous = chapters[index - 1].title if index else "研究背景"
            following = chapters[index + 1].title if index < len(chapters) - 1 else "全文总结"
            relation.previous_bridge = f"承接{previous}。"
            relation.next_bridge = f"为{following}做铺垫。"
            relation.required_questions = [f"{chapter.title}需要回答什么问题？"]
            relation.depends_on_facts = (project.brief.locked_facts if project.brief else []) or []
            relation.key_points = [chapter.purpose or chapter.title]
            relation.output_conclusions = [f"完成{chapter.title}的阶段性结论。"]
            relation.avoid_repeating = ["避免重复前文内容。"]
            db.add(relation)
            chapter.status = "relation_ready"
            relations.append(relation)
        project.status = "relations_ready"
        db.commit()
        for relation in relations:
            db.refresh(relation)
        return relations

    @classmethod
    def generate_draft(
        cls,
        db: Session,
        chapter_id: str,
        mode: str,
        user_instruction: str | None = None,
        client: LlmClient | None = None,
    ) -> ChapterDraft:
        chapter = db.get(Chapter, chapter_id)
        if chapter is None:
            raise ValueError("Chapter not found")
        project = chapter.project
        prior_summaries = list(
            db.scalars(
                select(ChapterSummary)
                .join(Chapter)
                .where(Chapter.project_id == project.id, Chapter.order < chapter.order)
            )
        )
        prompt = CHAPTER_DRAFT_PROMPT.format(
            project_type=project.type,
            project_title=project.title,
            project_brief=project.brief,
            outline=project.chapters,
            previous_summaries=prior_summaries,
            current_chapter=chapter,
            current_relation=chapter.relation,
            related_materials=project.materials,
            user_instruction=user_instruction or "",
        )
        llm = cls._client(client)
        content = llm.complete(prompt) if not isinstance(llm, MockLlmClient) else (
            f"# {chapter.title}\n\n{chapter.purpose or '本章围绕项目主题展开论述。'}"
        )
        version = db.scalar(
            select(func.coalesce(func.max(ChapterDraft.version), 0)).where(ChapterDraft.chapter_id == chapter.id)
        ) + 1
        draft = ChapterDraft(
            chapter_id=chapter.id,
            version=version,
            content=content,
            prompt_snapshot={"prompt": prompt, "user_instruction": user_instruction},
            generation_mode=mode,
        )
        chapter.status = "drafted"
        project.status = "drafting_chapters"
        return cls._commit_and_refresh(db, draft)

    @classmethod
    def generate_summary(
        cls, db: Session, chapter_id: str, client: LlmClient | None = None
    ) -> ChapterSummary:
        chapter = db.get(Chapter, chapter_id)
        if chapter is None:
            raise ValueError("Chapter not found")
        draft = db.scalar(
            select(ChapterDraft)
            .where(ChapterDraft.chapter_id == chapter.id)
            .order_by(ChapterDraft.version.desc())
        )
        if draft is None:
            raise ValueError("Chapter draft not found")
        prompt = CHAPTER_SUMMARY_PROMPT.format(chapter_title=chapter.title, chapter_content=draft.content)
        llm = cls._client(client)
        if not isinstance(llm, MockLlmClient):
            llm.complete(prompt)
        summary = ChapterSummary(
            chapter_id=chapter.id,
            summary=f"{chapter.title}概述了本章的核心内容。",
            key_conclusions=[chapter.purpose or chapter.title],
            used_facts=(chapter.project.brief.locked_facts if chapter.project.brief else []) or [],
            forward_implications=[chapter.relation.next_bridge] if chapter.relation else [],
        )
        return cls._commit_and_refresh(db, summary)

    @classmethod
    def review_consistency(
        cls, db: Session, project_id: str, client: LlmClient | None = None
    ) -> list[ConsistencyIssue]:
        project = ProjectService.get_project_or_404(db, project_id)
        chapters = list(db.scalars(select(Chapter).where(Chapter.project_id == project.id).order_by(Chapter.order)))
        drafts = list(
            db.scalars(select(ChapterDraft).join(Chapter).where(Chapter.project_id == project.id))
        )
        prompt = CONSISTENCY_REVIEW_PROMPT.format(
            project_brief=project.brief,
            outline=chapters,
            relations=[chapter.relation for chapter in chapters],
            chapter_drafts=drafts,
        )
        llm = cls._client(client)
        if not isinstance(llm, MockLlmClient):
            llm.complete(prompt)
        issue = ConsistencyIssue(
            project_id=project.id,
            severity="low",
            type="structure_review",
            description="请确认各章节内容与大纲保持一致。",
            suggestion="根据章节关系补充必要的过渡说明。",
        )
        project.status = "review_ready"
        return [cls._commit_and_refresh(db, issue)]
