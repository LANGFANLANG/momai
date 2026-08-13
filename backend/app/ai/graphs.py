from collections.abc import Callable
from typing import Any


GenerationNode = Callable[[dict[str, Any]], dict[str, Any]]


class SequentialWorkflow:
    def __init__(self, nodes: tuple[GenerationNode, ...]):
        self.nodes = nodes

    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        state = dict(state)
        for node in self.nodes:
            state = node(state)
        return state


def _workflow(*nodes: GenerationNode) -> SequentialWorkflow:
    return SequentialWorkflow(nodes)


def build_brief_workflow(*nodes: GenerationNode):
    return _workflow(*nodes)


def build_outline_workflow(*nodes: GenerationNode):
    return _workflow(*nodes)


def build_relations_workflow(*nodes: GenerationNode):
    return _workflow(*nodes)


def build_chapter_draft_workflow(*nodes: GenerationNode):
    return _workflow(*nodes)


def build_chapter_summary_workflow(*nodes: GenerationNode):
    return _workflow(*nodes)


def build_consistency_review_workflow(*nodes: GenerationNode):
    return _workflow(*nodes)


def build_consistency_fix_workflow(*nodes: GenerationNode):
    return _workflow(*nodes)


# Backwards-compatible builder names for callers using the original task brief.
build_brief_graph = build_brief_workflow
build_outline_graph = build_outline_workflow
build_relation_graph = build_relations_workflow
build_chapter_draft_graph = build_chapter_draft_workflow
build_chapter_summary_graph = build_chapter_summary_workflow
build_consistency_review_graph = build_consistency_review_workflow
build_consistency_fix_graph = build_consistency_fix_workflow
