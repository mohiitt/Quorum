"""Fake LLM client for testing validators that use Anthropic."""

from __future__ import annotations

from quorum.contracts.interfaces import LLMClient


class FakeLLMClient(LLMClient):
    """Returns a preset response without making any network calls."""

    def __init__(self, response: str = '{"verdict": "accepted", "confidence": 0.9, "rationale": "Fake LLM response"}') -> None:
        self._response = response
        self.calls: list[dict] = []

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> str:
        self.calls.append(
            {"system": system_prompt, "user": user_message, "max_tokens": max_tokens}
        )
        return self._response
