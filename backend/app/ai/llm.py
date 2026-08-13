from abc import ABC, abstractmethod
import json
import logging

import httpx

from app.ai.json_util import LlmError, LlmJsonError, loads_llm_json
from app.core.config import get_settings

logger = logging.getLogger(__name__)
DEFAULT_MAX_TOKENS = 8192
RETRY_MAX_TOKENS = 16384


class LlmClient(ABC):
    @abstractmethod
    def complete_json(self, prompt: str) -> dict:
        """Return a JSON object for a fully rendered prompt."""

    @abstractmethod
    def complete_markdown(self, prompt: str) -> str:
        """Return Markdown for a fully rendered prompt."""


class DeepSeekClient(LlmClient):
    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-v4-flash"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        if model != "deepseek-v4-flash":
            raise ValueError("Only the deepseek-v4-flash model is supported")
        self.model = "deepseek-v4-flash"

    def _complete(
        self, prompt: str, *, json_object: bool = False, max_tokens: int = DEFAULT_MAX_TOKENS
    ) -> tuple[str, str]:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "thinking": {"type": "disabled"},
            "max_tokens": max_tokens,
        }
        if json_object:
            payload["response_format"] = {"type": "json_object"}
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=180.0,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.TimeoutException as error:
            raise LlmError("模型响应超时，请再试一次。") from error
        except httpx.HTTPStatusError as error:
            raise LlmError(
                f"模型服务返回错误（{error.response.status_code}），请再试一次。"
            ) from error
        except httpx.HTTPError as error:
            raise LlmError("无法连接模型服务，请检查网络后重试。") from error
        except json.JSONDecodeError as error:
            raise LlmError("模型服务返回了无法解析的响应，请再试一次。") from error
        try:
            choice = body["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError) as error:
            raise LlmError("模型服务返回的数据不完整，请再试一次。") from error
        content = (message.get("content") or "").strip()
        if not content:
            content = (message.get("reasoning_content") or "").strip()
        return content, choice.get("finish_reason") or "stop"

    def complete_json(self, prompt: str) -> dict:
        content, finish_reason = self._complete(prompt, json_object=True)
        try:
            return loads_llm_json(content)
        except LlmJsonError as error:
            logger.warning("Invalid LLM JSON (%s), retrying once", error)
            retry_prompt = (
                prompt
                + "\n\n只输出一个合法 JSON 对象。属性之间必须有逗号；"
                "字符串内不要使用英文双引号，引用请用「」。不要输出 Markdown。"
            )
            max_tokens = RETRY_MAX_TOKENS if finish_reason == "length" else DEFAULT_MAX_TOKENS
            content, _ = self._complete(retry_prompt, json_object=True, max_tokens=max_tokens)
            return loads_llm_json(content)

    def complete_markdown(self, prompt: str) -> str:
        content, _ = self._complete(prompt)
        return content


class MockLlmClient(LlmClient):
    def complete_json(self, prompt: str) -> dict:
        return {}

    def complete_markdown(self, prompt: str) -> str:
        return prompt


def get_llm_client() -> LlmClient:
    settings = get_settings()
    if not settings.deepseek_v4:
        return MockLlmClient()
    return DeepSeekClient(settings.deepseek_v4, settings.deepseek_base_url, settings.deepseek_model)
