from abc import ABC, abstractmethod
import json

import httpx

from app.core.config import get_settings


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

    def _complete(self, prompt: str, *, json_object: bool = False) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "thinking": {"type": "disabled"},
        }
        if json_object:
            payload["response_format"] = {"type": "json_object"}
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=180.0,
        )
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]
        content = (message.get("content") or "").strip()
        if not content:
            content = (message.get("reasoning_content") or "").strip()
        return content

    def complete_json(self, prompt: str) -> dict:
        content = self._complete(prompt, json_object=True).strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("DeepSeek JSON completion must be an object")
        return parsed

    def complete_markdown(self, prompt: str) -> str:
        return self._complete(prompt)


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
