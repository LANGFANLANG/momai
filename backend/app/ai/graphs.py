from collections.abc import Callable
from typing import Any


def _build_sequential_graph(*nodes: Callable[[dict[str, Any]], dict[str, Any]]):
    def invoke(state: dict[str, Any]) -> dict[str, Any]:
        for node in nodes:
            state = node(state)
        return state

    return invoke


def build_brief_graph(*nodes):
    return _build_sequential_graph(*nodes)


def build_outline_graph(*nodes):
    return _build_sequential_graph(*nodes)


def build_relation_graph(*nodes):
    return _build_sequential_graph(*nodes)


def build_chapter_draft_graph(*nodes):
    return _build_sequential_graph(*nodes)


def build_chapter_summary_graph(*nodes):
    return _build_sequential_graph(*nodes)


def build_consistency_review_graph(*nodes):
    return _build_sequential_graph(*nodes)
