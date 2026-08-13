from pydantic import BaseModel, ValidationError
import httpx
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.ai.llm import LlmClient, MockLlmClient, get_llm_client
from app.ai.graphs import (
    build_brief_workflow,
    build_chapter_draft_workflow,
    build_chapter_summary_workflow,
    build_consistency_fix_workflow,
    build_consistency_review_workflow,
    build_outline_workflow,
    build_paper_abstract_workflow,
    build_relations_workflow,
)
from app.ai.prompt_payloads import (
    as_prompt_json,
    brief_payload,
    chapter_relations_payload,
    current_chapter_payload,
    current_relation_payload,
    materials_payload,
    outline_payload,
    summaries_payload,
)
from app.ai.prompts import (
    BRIEF_PROMPT,
    CHAPTER_DRAFT_PROMPT,
    CHAPTER_SUMMARY_PROMPT,
    CONSISTENCY_FIX_CHAPTER_PROMPT,
    CONSISTENCY_FIX_PROMPT,
    CONSISTENCY_REVIEW_PROMPT,
    OUTLINE_PROMPT,
    PAPER_ABSTRACT_PROMPT,
    RELATION_PROMPT,
)
from app.db.models import (
    Chapter,
    ChapterDraft,
    ChapterRelation,
    ChapterSummary,
    ConsistencyIssue,
    PaperAbstract,
    ProjectBrief,
)
from app.schemas.abstract import PaperAbstractGeneration
from app.schemas.brief import ProjectBriefGeneration
from app.schemas.chapter import (
    ChapterGeneration,
    OutlineGeneration,
    RelationsGeneration,
    ChapterSummaryGeneration,
)
from app.schemas.review import ChapterContentUpdate, ConsistencyFixGeneration, ConsistencyReviewGeneration
from app.services.chapters import list_chapters_in_hierarchy_order
from app.services.markdown_sections import extract_markdown_section, titles_match
from app.services.projects import ProjectService


class OutlineRegenerationConflict(Exception):
    pass


class ChapterDraftRequired(Exception):
    pass


class ConsistencyFixConflict(Exception):
    pass


class ConsistencyFixFailed(Exception):
    pass


class GenerationService:
    @staticmethod
    def _client(client: LlmClient | None) -> LlmClient:
        return client or get_llm_client()

    @staticmethod
    def _validate_generation(data: dict, model: type[BaseModel]):
        try:
            return model.model_validate(data)
        except ValidationError as original:
            for value in data.values():
                if isinstance(value, dict):
                    try:
                        return model.model_validate(value)
                    except ValidationError:
                        continue
            raise original

    @staticmethod
    def _commit_and_refresh(db: Session, row):
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def _latest_drafts_by_chapter(db: Session, project_id: str) -> dict[str, ChapterDraft]:
        latest_versions = (
            select(
                ChapterDraft.chapter_id,
                func.max(ChapterDraft.version).label("version"),
            )
            .join(Chapter)
            .where(Chapter.project_id == project_id)
            .group_by(ChapterDraft.chapter_id)
            .subquery()
        )
        drafts = db.scalars(
            select(ChapterDraft).join(
                latest_versions,
                and_(
                    ChapterDraft.chapter_id == latest_versions.c.chapter_id,
                    ChapterDraft.version == latest_versions.c.version,
                ),
            )
        )
        return {draft.chapter_id: draft for draft in drafts}

    @staticmethod
    def _chapter_by_title(chapters: list[Chapter], title: str) -> Chapter | None:
        for chapter in chapters:
            if chapter.title == title:
                return chapter
        return next(
            (chapter for chapter in chapters if titles_match(chapter.title, title)),
            None,
        )

    @classmethod
    def _resolve_draft_owner(
        cls,
        chapters: list[Chapter],
        draft_by_chapter: dict[str, ChapterDraft],
        title: str,
        chapter_id: str | None = None,
    ) -> Chapter | None:
        by_id = {chapter.id: chapter for chapter in chapters}
        chapter = next((item for item in chapters if item.id == chapter_id), None) if chapter_id else None
        chapter = chapter or cls._chapter_by_title(chapters, title)

        def owner_of(target: Chapter) -> Chapter | None:
            if target.id in draft_by_chapter:
                return target
            current = target
            while current.parent_id:
                parent = by_id.get(current.parent_id)
                if parent is None:
                    break
                if parent.id in draft_by_chapter:
                    return parent
                current = parent
            for candidate in chapters:
                draft = draft_by_chapter.get(candidate.id)
                if draft and extract_markdown_section(draft.content, target.title, target.level):
                    return candidate
            return None

        if chapter is not None:
            owner = owner_of(chapter)
            if owner is not None:
                return owner
        for candidate in chapters:
            draft = draft_by_chapter.get(candidate.id)
            if draft and extract_markdown_section(draft.content, title):
                return candidate
        return None

    @staticmethod
    def _draft_prompt_context(
        chapters: list[Chapter], draft_by_chapter: dict[str, ChapterDraft]
    ) -> list[dict]:
        return [
            {
                "chapter_id": chapter.id,
                "chapter_title": chapter.title,
                "version": draft_by_chapter[chapter.id].version,
                "content": draft_by_chapter[chapter.id].content,
            }
            for chapter in chapters
            if chapter.id in draft_by_chapter
        ]

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
            project_type=project.type,
            project_title=project.title,
            major=project.major or "未填写",
            school=project.school or "未填写",
            target_word_count=project.target_word_count or "未填写",
            requirements=project.requirements or "未填写",
        )
        llm = cls._client(client)
        def generate(state):
            if not isinstance(llm, MockLlmClient):
                return {
                    **state,
                    "result": cls._validate_generation(
                        llm.complete_json(state["prompt"]),
                        ProjectBriefGeneration,
                    ),
                }
            return {
                **state,
                "result": ProjectBriefGeneration(
                title_explanation=project.title,
                background=(context.background if context else None) or f"围绕《{project.title}》整理研究背景与应用需求。",
                core_problem=(context.problem if context else None) or f"明确《{project.title}》需要解决的核心问题。",
                goal=(context.goal if context else None) or f"完成《{project.title}》的分析、设计与实现。",
                significance="说明该选题的理论与实践意义。",
                technical_route=(context.architecture if context else None) or "按照需求、设计、实现与测试推进。",
                modules=(context.modules if context else None) or [],
                expected_result="形成结构完整的项目报告初稿。",
                writing_boundary="围绕项目标题展开，不编造未给出的实验数据或学校格式要求。",
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
            project_brief=brief_payload(project.brief),
            outline_preference=outline_preference or "默认结构",
        )
        llm = cls._client(client)
        def generate(state):
            result = (
                cls._mock_outline(project.id, project.target_word_count)
                if isinstance(llm, MockLlmClient)
                else cls._validate_generation(
                    llm.complete_json(state["prompt"]), OutlineGeneration
                )
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

    @staticmethod
    def _descendants(parent: Chapter, chapters: list[Chapter]) -> list[Chapter]:
        children_by_parent: dict[str | None, list[Chapter]] = {}
        for chapter in chapters:
            children_by_parent.setdefault(chapter.parent_id, []).append(chapter)
        descendants: list[Chapter] = []

        def walk(parent_id: str) -> None:
            for child in children_by_parent.get(parent_id, []):
                descendants.append(child)
                walk(child.id)

        walk(parent.id)
        return descendants

    @classmethod
    def _mark_matched_descendants_drafted(
        cls, chapters: list[Chapter], parent: Chapter, markdown: str
    ) -> None:
        for child in cls._descendants(parent, chapters):
            if child.status not in {"planned", "relation_ready", "drafting"}:
                continue
            if extract_markdown_section(markdown, child.title, child.level):
                child.status = "drafted"

    @classmethod
    def sync_matched_child_draft_statuses(cls, db: Session, project_id: str) -> None:
        chapters = list_chapters_in_hierarchy_order(db, project_id)
        latest_drafts: dict[str, ChapterDraft] = {}
        for draft in db.scalars(
            select(ChapterDraft)
            .join(Chapter)
            .where(Chapter.project_id == project_id)
            .order_by(ChapterDraft.version.desc())
        ):
            latest_drafts.setdefault(draft.chapter_id, draft)
        for chapter in chapters:
            draft = latest_drafts.get(chapter.id)
            if draft is None:
                continue
            if chapter.status in {"planned", "relation_ready", "drafting"}:
                chapter.status = "drafted"
            cls._mark_matched_descendants_drafted(chapters, chapter, draft.content)
        db.commit()

    @classmethod
    def generate_relations(cls, db: Session, project_id: str, client: LlmClient | None = None) -> list[ChapterRelation]:
        project = ProjectService.get_project_or_404(db, project_id)
        chapters = list_chapters_in_hierarchy_order(db, project.id)
        llm = cls._client(client)
        prompt = RELATION_PROMPT.format(
            project_brief=brief_payload(project.brief),
            outline=outline_payload(chapters),
        )
        def generate(state):
            if not isinstance(llm, MockLlmClient):
                result = cls._validate_generation(
                    llm.complete_json(state["prompt"]), RelationsGeneration
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
            project_type=project.type,
            project_title=project.title,
            project_brief=brief_payload(project.brief),
            outline=outline_payload(list_chapters_in_hierarchy_order(db, project.id)),
            previous_summaries=summaries_payload(prior_summaries),
            current_chapter=current_chapter_payload(chapter),
            current_relation=current_relation_payload(chapter.relation),
            related_materials=materials_payload(project.materials),
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
        cls._mark_matched_descendants_drafted(
            list_chapters_in_hierarchy_order(db, project.id), chapter, content
        )
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
                else cls._validate_generation(
                    llm.complete_json(state["prompt"]), ChapterSummaryGeneration
                )
            )
            return {**state, "result": data}

        data = build_chapter_summary_workflow(generate).invoke({"prompt": prompt})[
            "result"
        ]
        return cls._commit_and_refresh(db, ChapterSummary(chapter_id=chapter.id, **data.model_dump()))

    @classmethod
    def generate_paper_abstract(
        cls, db: Session, project_id: str, client: LlmClient | None = None
    ) -> PaperAbstract:
        project = ProjectService.get_project_or_404(db, project_id)
        chapters = list_chapters_in_hierarchy_order(db, project.id)
        draft_by_chapter = cls._latest_drafts_by_chapter(db, project.id)
        if not draft_by_chapter:
            raise ChapterDraftRequired(
                "Generate chapter drafts before generating the paper abstract."
            )
        prompt = PAPER_ABSTRACT_PROMPT.format(
            project_type=project.type,
            project_title=project.title,
            project_brief=brief_payload(project.brief),
            chapter_drafts=as_prompt_json(
                cls._draft_prompt_context(chapters, draft_by_chapter)
            ),
        )
        llm = cls._client(client)

        def generate(state):
            if isinstance(llm, MockLlmClient):
                modules = (project.brief.modules if project.brief else None) or []
                module_text = "、".join(modules) if modules else "相关模块"
                goal = (project.brief.goal if project.brief else None) or f"完成《{project.title}》"
                data = PaperAbstractGeneration(
                    title_en=project.title,
                    abstract_zh=(
                        f"本文围绕《{project.title}》展开研究。{goal}"
                        f"主要工作包括{module_text}。"
                    ),
                    abstract_en=f"This paper studies {project.title}. {goal}",
                    keywords_zh=modules[:4] or [project.title],
                    keywords_en=modules[:4] or [project.title],
                )
            else:
                data = cls._validate_generation(
                    llm.complete_json(state["prompt"]), PaperAbstractGeneration
                )
            return {**state, "result": data}

        data = build_paper_abstract_workflow(generate).invoke({"prompt": prompt})["result"]
        abstract = project.paper_abstract or PaperAbstract(project_id=project.id)
        for field, value in data.model_dump().items():
            setattr(abstract, field, value)
        return cls._commit_and_refresh(db, abstract)

    @classmethod
    def review_consistency(cls, db: Session, project_id: str, client: LlmClient | None = None) -> list[ConsistencyIssue]:
        project = ProjectService.get_project_or_404(db, project_id)
        chapters = list_chapters_in_hierarchy_order(db, project.id)
        draft_by_chapter = cls._latest_drafts_by_chapter(db, project.id)
        draft_context = cls._draft_prompt_context(chapters, draft_by_chapter)
        prompt = CONSISTENCY_REVIEW_PROMPT.format(
            project_brief=brief_payload(project.brief),
            outline=outline_payload(chapters),
            relations=chapter_relations_payload(chapters),
            chapter_drafts=as_prompt_json(draft_context),
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
                else cls._validate_generation(
                    llm.complete_json(state["prompt"]), ConsistencyReviewGeneration
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

    @classmethod
    def fix_consistency_issue(
        cls,
        db: Session,
        project_id: str,
        issue_id: str,
        client: LlmClient | None = None,
    ) -> tuple[ConsistencyIssue, list[ChapterDraft], str | None]:
        project = ProjectService.get_project_or_404(db, project_id)
        issue = db.get(ConsistencyIssue, issue_id)
        if issue is None or issue.project_id != project.id:
            raise ConsistencyFixConflict("Consistency issue not found")
        if issue.status != "open":
            raise ConsistencyFixConflict("Only open consistency issues can be auto-fixed.")
        chapters = list_chapters_in_hierarchy_order(db, project.id)
        draft_by_chapter = cls._latest_drafts_by_chapter(db, project.id)
        if not draft_by_chapter:
            raise ConsistencyFixConflict("Generate chapter drafts before applying an AI fix.")
        related = next((chapter for chapter in chapters if chapter.id == issue.chapter_id), None)
        plan_prompt = CONSISTENCY_FIX_PROMPT.format(
            project_brief=brief_payload(project.brief),
            outline=outline_payload(chapters),
            issue_type=issue.type,
            severity=issue.severity,
            description=issue.description,
            suggestion=issue.suggestion or "",
            related_chapter=related.title if related else "未指定，可能涉及多章",
            chapter_drafts=as_prompt_json(cls._draft_prompt_context(chapters, draft_by_chapter)),
        )
        llm = cls._client(client)

        def generate(state):
            if isinstance(llm, MockLlmClient):
                target_id = (
                    issue.chapter_id
                    if issue.chapter_id in draft_by_chapter
                    else next(iter(draft_by_chapter))
                )
                target = next(chapter for chapter in chapters if chapter.id == target_id)
                data = ConsistencyFixGeneration(
                    chapter_updates=[{"chapter_title": target.title}],
                    fix_summary="已根据建议修订相关章节。",
                )
            else:
                try:
                    data = cls._validate_generation(
                        llm.complete_json(state["prompt"]), ConsistencyFixGeneration
                    )
                except (ValidationError, ValueError, httpx.HTTPError) as error:
                    raise ConsistencyFixFailed("模型未能返回可解析的修复方案。") from error
            return {**state, "result": data}

        data = build_consistency_fix_workflow(generate).invoke({"prompt": plan_prompt})["result"]
        planned = list(data.chapter_updates)
        if not planned and related:
            planned = [ChapterContentUpdate(chapter_title=related.title, chapter_id=related.id)]
        targets: dict[str, list[str]] = {}
        for item in planned:
            owner = cls._resolve_draft_owner(
                chapters, draft_by_chapter, item.chapter_title, item.chapter_id
            )
            if owner is None:
                continue
            titles = targets.setdefault(owner.id, [])
            if item.chapter_title not in titles:
                titles.append(item.chapter_title)
        if not targets:
            raise ConsistencyFixConflict("The model did not return any matching chapter updates.")

        created: list[ChapterDraft] = []
        for chapter_id, titles in targets.items():
            chapter = next(item for item in chapters if item.id == chapter_id)
            current = draft_by_chapter[chapter.id]
            if isinstance(llm, MockLlmClient):
                content = f"{current.content}\n\n已按一致性建议修订。"
                rewrite_prompt = plan_prompt
            else:
                rewrite_prompt = CONSISTENCY_FIX_CHAPTER_PROMPT.format(
                    issue_type=issue.type,
                    severity=issue.severity,
                    description=issue.description,
                    suggestion=issue.suggestion or "",
                    target_titles="、".join(titles),
                    chapter_title=chapter.title,
                    chapter_content=current.content,
                )
                try:
                    content = llm.complete_markdown(rewrite_prompt).strip()
                except (ValidationError, ValueError, httpx.HTTPError) as error:
                    raise ConsistencyFixFailed("模型未能返回修订正文。") from error
                if not content:
                    raise ConsistencyFixFailed("模型返回的修订正文为空。")
            version = (
                db.scalar(
                    select(func.coalesce(func.max(ChapterDraft.version), 0)).where(
                        ChapterDraft.chapter_id == chapter.id
                    )
                )
                + 1
            )
            draft = ChapterDraft(
                chapter_id=chapter.id,
                version=version,
                content=content,
                prompt_snapshot={
                    "plan_prompt": plan_prompt,
                    "prompt": rewrite_prompt,
                    "issue_id": issue.id,
                    "suggestion": issue.suggestion,
                },
                generation_mode="rewrite",
            )
            db.add(draft)
            created.append(draft)
            chapter.status = "drafted"
            cls._mark_matched_descendants_drafted(chapters, chapter, content)
        issue.status = "fixed"
        db.commit()
        for draft in created:
            db.refresh(draft)
        db.refresh(issue)
        return issue, created, data.fix_summary
