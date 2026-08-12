from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings


class LlmClient(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Return a completion for a fully rendered prompt."""


class DeepSeekClient(LlmClient):
    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-flash"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete(self, prompt: str) -> str:
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "messages": [{"role": "user", "content": prompt}]},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


class MockLlmClient(LlmClient):
    def complete(self, prompt: str) -> str:
        return prompt


def get_llm_client() -> LlmClient:
    settings = get_settings()
    if not settings.deepseek_v4:
        return MockLlmClient()
    return DeepSeekClient(settings.deepseek_v4, settings.deepseek_base_url, settings.deepseek_model)
