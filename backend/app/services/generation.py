from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.ai.llm import LlmClient, MockLlmClient, get_llm_client
from app.ai.graphs import (
    build_brief_workflow,
    build_chapter_draft_workflow,
    build_chapter_summary_workflow,
    build_consistency_review_workflow,
    build_outline_workflow,
    build_relations_workflow,
)
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
    ProjectBrief,
)
from app.schemas.brief import ProjectBriefGeneration
from app.schemas.chapter import (
    ChapterGeneration,
    OutlineGeneration,
    RelationsGeneration,
    ChapterSummaryGeneration,
)
from app.schemas.review import ConsistencyReviewGeneration
from app.services.chapters import list_chapters_in_hierarchy_order
from app.services.projects import ProjectService


class OutlineRegenerationConflict(Exception):
    pass


class ChapterDraftRequired(Exception):
    pass


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

    @staticmethod
    def _mock_outline(project_id: str, target_word_count: int | None) -> list[Chapter]:
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
        word_count = (target_word_count or 8000) // len(titles)
        return [
            Chapter(
                project_id=project_id,
                title=title,
                level=1,
                order=index,
                purpose=f"完成{title}的论述。",
                suggested_word_count=word_count,
            )
            for index, title in enumerate(titles, start=1)
        ]

    @classmethod
    def _persist_outline_chapter(
        cls,
        db: Session,
        project_id: str,
        item: ChapterGeneration,
        parent_id: str | None = None,
    ) -> Chapter:
        chapter = Chapter(
            project_id=project_id,
            parent_id=parent_id,
            **item.model_dump(exclude={"children"}),
        )
        db.add(chapter)
        db.flush()
        for child in item.children:
            cls._persist_outline_chapter(db, project_id, child, chapter.id)
        return chapter

    @classmethod
    def generate_brief(cls, db: Session, project_id: str, client: LlmClient | None = None) -> ProjectBrief:
        project = ProjectService.get_project_or_404(db, project_id)
        context = project.context
        prompt = BRIEF_PROMPT.format(
            project_type=project.type, project_title=project.title, project_context=context
        )
        llm = cls._client(client)
        def generate(state):
            if not isinstance(llm, MockLlmClient):
                return {
                    **state,
                    "result": ProjectBriefGeneration.model_validate(
                        llm.complete_json(state["prompt"])
                    ),
                }
            return {
                **state,
                "result": ProjectBriefGeneration(
                title_explanation=project.title,
                background=(context.background if context else None) or "围绕项目主题整理研究背景。",
                core_problem=(context.problem if context else None) or "明确项目需要解决的核心问题。",
                goal=(context.goal if context else None) or "完成项目目标的分析与设计。",
                significance="说明项目的理论与实践意义。",
                technical_route=(context.architecture if context else None) or "按照需求、设计、实现与测试推进。",
                modules=(context.modules if context else None) or [],
                expected_result="形成结构完整的项目报告初稿。",
                writing_boundary="仅基于用户提供的项目事实写作。",
                locked_facts=[project.title, *((context.modules if context else None) or [])],
                ),
            }

        data = build_brief_workflow(generate).invoke({"prompt": prompt})["result"]
        brief = project.brief or ProjectBrief(project_id=project.id)
        for field, value in data.model_dump().items():
            setattr(brief, field, value)
        project.status = "brief_ready"
        return cls._commit_and_refresh(db, brief)

    @classmethod
    def generate_outline(
        cls, db: Session, project_id: str, outline_preference: str | None = None,
        client: LlmClient | None = None, force: bool = False,
    ) -> list[Chapter]:
        project = ProjectService.get_project_or_404(db, project_id)
        if not force and cls._outline_has_downstream_work(db, project.id):
            raise OutlineRegenerationConflict(
                "Outline regeneration would delete chapter relations, drafts, or summaries. "
                "Retry with force=true only after confirming that this work may be deleted."
            )
        prompt = OUTLINE_PROMPT.format(
            project_type=project.type,
            target_word_count=project.target_word_count,
            requirements=project.requirements,
            project_brief=project.brief,
            outline_preference=outline_preference or "默认结构",
        )
        llm = cls._client(client)
        def generate(state):
            result = (
                cls._mock_outline(project.id, project.target_word_count)
                if isinstance(llm, MockLlmClient)
                else OutlineGeneration.model_validate(llm.complete_json(state["prompt"]))
            )
            return {**state, "result": result}

        output = build_outline_workflow(generate).invoke({"prompt": prompt})["result"]
        for chapter in [item for item in list(project.chapters) if item.parent_id is None]:
            db.delete(chapter)
        db.flush()
        if isinstance(llm, MockLlmClient):
            db.add_all(output)
        else:
            for item in output.chapters:
                cls._persist_outline_chapter(db, project.id, item)
        project.status = "outline_ready"
        db.commit()
        return list_chapters_in_hierarchy_order(db, project.id)

    @staticmethod
    def _outline_has_downstream_work(db: Session, project_id: str) -> bool:
        downstream_models = (ChapterRelation, ChapterDraft, ChapterSummary)
        return any(
            db.scalar(
                select(model.id)
                .join(Chapter)
                .where(Chapter.project_id == project_id)
                .limit(1)
            )
            is not None
            for model in downstream_models
        )

    @classmethod
    def generate_relations(cls, db: Session, project_id: str, client: LlmClient | None = None) -> list[ChapterRelation]:
        project = ProjectService.get_project_or_404(db, project_id)
        chapters = list_chapters_in_hierarchy_order(db, project.id)
        llm = cls._client(client)
        prompt = RELATION_PROMPT.format(project_brief=project.brief, outline=chapters)
        def generate(state):
            if not isinstance(llm, MockLlmClient):
                result = RelationsGeneration.model_validate(
                    llm.complete_json(state["prompt"])
                ).relations
                return {**state, "result": [item.model_dump() for item in result]}
            items = []
            for index, chapter in enumerate(chapters):
                previous = chapters[index - 1].title if index else "研究背景"
                following = chapters[index + 1].title if index < len(chapters) - 1 else "全文总结"
                items.append({
                    "chapter_title": chapter.title,
                    "previous_bridge": f"承接{previous}。",
                    "next_bridge": f"为{following}做铺垫。",
                    "required_questions": [f"{chapter.title}需要回答什么问题？"],
                    "depends_on_facts": (project.brief.locked_facts if project.brief else []) or [],
                    "key_points": [chapter.purpose or chapter.title],
                    "output_conclusions": [f"完成{chapter.title}的阶段性结论。"],
                    "avoid_repeating": ["避免重复前文内容。"],
                })
            return {**state, "result": items}

        items = build_relations_workflow(generate).invoke({"prompt": prompt})["result"]
        chapters_by_title = {chapter.title: chapter for chapter in chapters}
        relations = []
        for item in items:
            chapter = chapters_by_title.get(item.pop("chapter_title"))
            if chapter is None:
                continue
            item.pop("purpose", None)
            relation = chapter.relation or ChapterRelation(chapter_id=chapter.id)
            for field, value in item.items():
                setattr(relation, field, value)
            db.add(relation)
            chapter.status = "relation_ready"
            relations.append(relation)
        project.status = "relations_ready"
        db.commit()
        for relation in relations:
            db.refresh(relation)
        return relations

    @classmethod
    def generate_draft(cls, db: Session, chapter_id: str, mode: str, user_instruction: str | None = None, client: LlmClient | None = None) -> ChapterDraft:
        chapter = db.get(Chapter, chapter_id)
        if chapter is None:
            raise ValueError("Chapter not found")
        project = chapter.project
        prior_summaries = list(db.scalars(select(ChapterSummary).join(Chapter).where(Chapter.project_id == project.id, Chapter.order < chapter.order)))
        prompt = CHAPTER_DRAFT_PROMPT.format(
            project_type=project.type, project_title=project.title, project_brief=project.brief,
            outline=project.chapters, previous_summaries=prior_summaries, current_chapter=chapter,
            current_relation=chapter.relation, related_materials=project.materials,
            user_instruction=user_instruction or "",
        )
        llm = cls._client(client)
        def generate(state):
            content = (
                f"# {chapter.title}\n\n{chapter.purpose or '本章围绕项目主题展开论述。'}"
                if isinstance(llm, MockLlmClient)
                else llm.complete_markdown(state["prompt"])
            )
            return {**state, "result": content}

        content = build_chapter_draft_workflow(generate).invoke({"prompt": prompt})["result"]
        version = db.scalar(select(func.coalesce(func.max(ChapterDraft.version), 0)).where(ChapterDraft.chapter_id == chapter.id)) + 1
        draft = ChapterDraft(chapter_id=chapter.id, version=version, content=content,
            prompt_snapshot={"prompt": prompt, "user_instruction": user_instruction}, generation_mode=mode)
        chapter.status = "drafted"
        project.status = "drafting_chapters"
        return cls._commit_and_refresh(db, draft)

    @classmethod
    def generate_summary(cls, db: Session, chapter_id: str, client: LlmClient | None = None) -> ChapterSummary:
        chapter = db.get(Chapter, chapter_id)
        if chapter is None:
            raise ValueError("Chapter not found")
        draft = db.scalar(select(ChapterDraft).where(ChapterDraft.chapter_id == chapter.id).order_by(ChapterDraft.version.desc()))
        if draft is None:
            raise ChapterDraftRequired(
                "Generate a chapter draft before generating its summary."
            )
        prompt = CHAPTER_SUMMARY_PROMPT.format(chapter_title=chapter.title, chapter_content=draft.content)
        llm = cls._client(client)
        def generate(state):
            data = (
                ChapterSummaryGeneration(
                    summary=f"{chapter.title}概述了本章的核心内容。",
                    key_conclusions=[chapter.purpose or chapter.title],
                    used_facts=(
                        chapter.project.brief.locked_facts
                        if chapter.project.brief
                        else []
                    )
                    or [],
                    forward_implications=(
                        [chapter.relation.next_bridge] if chapter.relation else []
                    ),
                )
                if isinstance(llm, MockLlmClient)
                else ChapterSummaryGeneration.model_validate(
                    llm.complete_json(state["prompt"])
                )
            )
            return {**state, "result": data}

        data = build_chapter_summary_workflow(generate).invoke({"prompt": prompt})[
            "result"
        ]
        return cls._commit_and_refresh(db, ChapterSummary(chapter_id=chapter.id, **data.model_dump()))

    @classmethod
    def review_consistency(cls, db: Session, project_id: str, client: LlmClient | None = None) -> list[ConsistencyIssue]:
        project = ProjectService.get_project_or_404(db, project_id)
        chapters = list_chapters_in_hierarchy_order(db, project.id)
        latest_versions = (
            select(
                ChapterDraft.chapter_id,
                func.max(ChapterDraft.version).label("version"),
            )
            .join(Chapter)
            .where(Chapter.project_id == project.id)
            .group_by(ChapterDraft.chapter_id)
            .subquery()
        )
        drafts = list(
            db.scalars(
                select(ChapterDraft).join(
                    latest_versions,
                    and_(
                        ChapterDraft.chapter_id == latest_versions.c.chapter_id,
                        ChapterDraft.version == latest_versions.c.version,
                    ),
                )
            )
        )
        draft_by_chapter = {draft.chapter_id: draft for draft in drafts}
        draft_context = [
            {
                "chapter_id": chapter.id,
                "chapter_title": chapter.title,
                "version": draft_by_chapter[chapter.id].version,
                "content": draft_by_chapter[chapter.id].content,
            }
            for chapter in chapters
            if chapter.id in draft_by_chapter
        ]
        prompt = CONSISTENCY_REVIEW_PROMPT.format(
            project_brief=project.brief,
            outline=chapters,
            relations=[chapter.relation for chapter in chapters],
            chapter_drafts=draft_context,
        )
        llm = cls._client(client)
        def generate(state):
            data = (
                ConsistencyReviewGeneration(
                    issues=[
                        {
                            "severity": "low",
                            "type": "structure_review",
                            "description": "请确认各章节内容与大纲保持一致。",
                            "suggestion": "根据章节关系补充必要的过渡说明。",
                        }
                    ]
                )
                if isinstance(llm, MockLlmClient)
                else ConsistencyReviewGeneration.model_validate(
                    llm.complete_json(state["prompt"])
                )
            )
            return {**state, "result": data}

        data = build_consistency_review_workflow(generate).invoke({"prompt": prompt})[
            "result"
        ]
        chapters_by_title = {chapter.title: chapter for chapter in chapters}
        issues = []
        for item in data.issues:
            values = item.model_dump()
            chapter_title = values.pop("chapter_title")
            chapter = chapters_by_title.get(chapter_title) if chapter_title else None
            issues.append(ConsistencyIssue(project_id=project.id, chapter_id=chapter.id if chapter else None, **values))
        db.add_all(issues)
        project.status = "review_ready"
        db.commit()
        for issue in issues:
            db.refresh(issue)
        return issues
