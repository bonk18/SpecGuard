"""Provider-neutral LLM interface and errors."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProviderError(RuntimeError):
    """A clear, safe provider failure suitable for fallback handling."""


class LLMProvider(ABC):
    """Minimal interface used by the intelligence business logic."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return one JSON object matching the intermediate generation schema."""

        raise NotImplementedError
