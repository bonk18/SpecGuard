"""Groq chat-completions adapter isolated from intelligence business logic."""

from __future__ import annotations

import os
import time
from typing import Any

from app.intelligence.providers.base import LLMProvider, LLMProviderError


class GroqLLMProvider(LLMProvider):
    """Request strict JSON output from Groq with bounded transient retries."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("LLM_MODEL")
        timeout_value = timeout_seconds or float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
        self.timeout_seconds = timeout_value
        self.max_retries = max(0, max_retries)

    def _client(self) -> Any:
        try:
            from groq import Groq
        except ImportError as exc:
            raise LLMProviderError(
                "The Groq provider requires the 'groq' package"
            ) from exc
        return Groq(api_key=self.api_key, timeout=self.timeout_seconds, max_retries=0)

    @staticmethod
    def _is_transient(exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        transient_names = {
            "APIConnectionError",
            "APITimeoutError",
            "InternalServerError",
            "RateLimitError",
        }
        return (
            status_code in {408, 409, 429, 500, 502, 503, 504}
            or isinstance(exc, (TimeoutError, ConnectionError))
            or exc.__class__.__name__ in transient_names
        )

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise LLMProviderError("GROQ_API_KEY is not configured")
        if not self.model:
            raise LLMProviderError("LLM_MODEL is not configured for the Groq provider")
        client = self._client()
        for attempt in range(self.max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                content = response.choices[0].message.content
                if not content or not content.strip():
                    raise LLMProviderError("Groq returned an empty response")
                return content
            except LLMProviderError:
                raise
            except Exception as exc:
                if attempt < self.max_retries and self._is_transient(exc):
                    time.sleep(0.25 * (2**attempt))
                    continue
                message = str(exc).strip() or exc.__class__.__name__
                if self.api_key:
                    message = message.replace(self.api_key, "[REDACTED]")
                raise LLMProviderError(f"Groq generation failed: {message}") from exc
        raise LLMProviderError("Groq generation failed after retries")
