import json

import pytest

from app.ai.json_util import LlmJsonError, loads_llm_json


def test_loads_llm_json_strips_markdown_fence():
    assert loads_llm_json('```json\n{"ok": true}\n```') == {"ok": True}


def test_loads_llm_json_repairs_trailing_comma():
    assert loads_llm_json('{"chapters": [{"title": "绪论",},],}') == {
        "chapters": [{"title": "绪论"}]
    }


def test_loads_llm_json_repairs_missing_comma_before_next_key():
    raw = """
    {
      "chapters": [
        {
          "title": "绪论",
          "level": 1,
          "order": 1,
          "purpose": "介绍研究背景",
          "suggested_word_count": 1200
          "children": []
        }
      ]
    }
    """
    with pytest.raises(json.JSONDecodeError, match="Expecting ',' delimiter"):
        json.loads(raw)
    parsed = loads_llm_json(raw)
    assert parsed["chapters"][0]["title"] == "绪论"
    assert parsed["chapters"][0]["children"] == []
    assert parsed["chapters"][0]["suggested_word_count"] == 1200


def test_loads_llm_json_repairs_missing_comma_between_array_objects():
    raw = '{"chapters": [{"title": "绪论"} {"title": "设计"}]}'
    parsed = loads_llm_json(raw)
    assert [item["title"] for item in parsed["chapters"]] == ["绪论", "设计"]


def test_loads_llm_json_rejects_truncated_object():
    with pytest.raises(LlmJsonError, match="不是合法 JSON"):
        loads_llm_json('{"chapters": [{"title": "绪论"')
