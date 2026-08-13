from unittest.mock import Mock, patch

import pytest

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


def test_deepseek_client_rejects_invalid_model_name():
    with pytest.raises(ValueError, match="deepseek-v4-flash"):
        DeepSeekClient("sk-test", "https://api.deepseek.com", "deepseek-flash")
