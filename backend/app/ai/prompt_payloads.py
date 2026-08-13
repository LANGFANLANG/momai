import json
from typing import Any

from app.db.models import (
    Chapter,
    ChapterRelation,
    ChapterSummary,
    Material,
    ProjectBrief,
    ProjectContext,
)


def as_prompt_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def context_payload(context: ProjectContext | None) -> str:
    if context is None:
        return "未填写"
    return as_prompt_json(
        {
            "background": context.background,
            "problem": context.problem,
            "goal": context.goal,
            "scenario": context.scenario,
            "target_users": context.target_users,
            "methods": context.methods,
            "technologies": context.technologies,
            "modules": context.modules,
            "architecture": context.architecture,
            "environment": context.environment,
            "data_sources": context.data_sources,
            "experiments": context.experiments,
            "innovations": context.innovations,
            "constraints": context.constraints,
            "writing_prefs": context.writing_prefs,
        }
    )


def brief_payload(brief: ProjectBrief | None) -> str:
    if brief is None:
        return "未生成"
    return as_prompt_json(
        {
            "title_explanation": brief.title_explanation,
            "background": brief.background,
            "core_problem": brief.core_problem,
            "goal": brief.goal,
            "significance": brief.significance,
            "technical_route": brief.technical_route,
            "modules": brief.modules,
            "expected_result": brief.expected_result,
            "writing_boundary": brief.writing_boundary,
            "missing_info": brief.missing_info,
            "locked_facts": brief.locked_facts,
        }
    )


def chapter_payload(chapter: Chapter) -> dict:
    return {
        "title": chapter.title,
        "level": chapter.level,
        "order": chapter.order,
        "purpose": chapter.purpose,
        "suggested_word_count": chapter.suggested_word_count,
    }


def outline_payload(chapters: list[Chapter]) -> str:
    return as_prompt_json([chapter_payload(chapter) for chapter in chapters])


def relation_payload(relation: ChapterRelation | None) -> dict | None:
    if relation is None:
        return None
    return {
        "previous_bridge": relation.previous_bridge,
        "next_bridge": relation.next_bridge,
        "required_questions": relation.required_questions,
        "depends_on_facts": relation.depends_on_facts,
        "key_points": relation.key_points,
        "output_conclusions": relation.output_conclusions,
        "avoid_repeating": relation.avoid_repeating,
    }


def current_chapter_payload(chapter: Chapter | None) -> str:
    if chapter is None:
        return "无"
    return as_prompt_json(chapter_payload(chapter))


def current_relation_payload(relation: ChapterRelation | None) -> str:
    payload = relation_payload(relation)
    return "未生成" if payload is None else as_prompt_json(payload)


def summaries_payload(summaries: list[ChapterSummary]) -> str:
    return as_prompt_json(
        [
            {
                "summary": item.summary,
                "key_conclusions": item.key_conclusions,
                "used_facts": item.used_facts,
                "forward_implications": item.forward_implications,
            }
            for item in summaries
        ]
    )


def materials_payload(materials: list[Material]) -> str:
    return as_prompt_json(
        [
            {"type": item.type, "title": item.title, "content": item.content}
            for item in materials
        ]
    )


def chapter_relations_payload(chapters: list[Chapter]) -> str:
    return as_prompt_json(
        [
            {"chapter_title": chapter.title, **(relation_payload(chapter.relation) or {})}
            for chapter in chapters
        ]
    )
