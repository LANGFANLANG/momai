from unittest.mock import Mock, patch

import httpx
import pytest

from app.ai.json_util import LlmError
from app.ai.llm import DeepSeekClient


def test_deepseek_client_sends_v4_flash_model():
    client = DeepSeekClient("sk-test", "https://api.deepseek.com")
    response = Mock()
    response.json.return_value = {"choices": [{"message": {"content": '{"ok": true}'}}]}
    response.raise_for_status.return_value = None

    with patch("app.ai.llm.httpx.post", return_value=response) as post:
        result = client.complete_json("prompt")

    assert result == {"ok": True}
    assert post.call_args.kwargs["json"]["model"] == "deepseek-v4-flash"
    assert post.call_args.kwargs["json"]["thinking"] == {"type": "disabled"}
    assert post.call_args.kwargs["json"]["response_format"] == {"type": "json_object"}
    assert post.call_args.kwargs["json"]["max_tokens"] == 8192
    assert post.call_args.kwargs["timeout"] == 180.0


def test_deepseek_client_uses_reasoning_content_when_message_content_is_empty():
    client = DeepSeekClient("sk-test", "https://api.deepseek.com")
    response = Mock()
    response.json.return_value = {
        "choices": [{"message": {"content": "", "reasoning_content": '{"ok": true}'}}]
    }
    response.raise_for_status.return_value = None

    with patch("app.ai.llm.httpx.post", return_value=response):
        assert client.complete_json("prompt") == {"ok": True}


def test_deepseek_client_repairs_missing_comma_without_retry():
    client = DeepSeekClient("sk-test", "https://api.deepseek.com")
    response = Mock()
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"title": "绪论", "suggested_word_count": 1200 "children": []}'
                },
                "finish_reason": "stop",
            }
        ]
    }
    response.raise_for_status.return_value = None

    with patch("app.ai.llm.httpx.post", return_value=response) as post:
        result = client.complete_json("prompt")

    assert result == {"title": "绪论", "suggested_word_count": 1200, "children": []}
    assert post.call_count == 1


def test_deepseek_client_retries_when_json_cannot_be_repaired():
    client = DeepSeekClient("sk-test", "https://api.deepseek.com")
    bad = Mock()
    bad.json.return_value = {
        "choices": [{"message": {"content": '{"ok": true'}, "finish_reason": "stop"}]
    }
    bad.raise_for_status.return_value = None
    good = Mock()
    good.json.return_value = {
        "choices": [{"message": {"content": '{"ok": true}'}, "finish_reason": "stop"}]
    }
    good.raise_for_status.return_value = None

    with patch("app.ai.llm.httpx.post", side_effect=[bad, good]) as post:
        assert client.complete_json("prompt") == {"ok": True}
    assert post.call_count == 2


def test_deepseek_client_maps_http_error_to_llm_error():
    client = DeepSeekClient("sk-test", "https://api.deepseek.com")
    response = Mock()
    response.status_code = 500
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "boom", request=Mock(), response=response
    )

    with patch("app.ai.llm.httpx.post", return_value=response):
        with pytest.raises(LlmError, match="模型服务返回错误"):
            client.complete_json("prompt")


def test_deepseek_client_rejects_invalid_model_name():
    with pytest.raises(ValueError, match="deepseek-v4-flash"):
        DeepSeekClient("sk-test", "https://api.deepseek.com", "deepseek-flash")
