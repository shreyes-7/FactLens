"""
Gemini LLM Provider Implementation (Optional Provider).
Preserved for backwards compatibility and provider flexibility.
"""

from typing import Any
import httpx

from backend.app.providers.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    """Optional Google Gemini API provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-flash",
        timeout: float = 60.0,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("Gemini API key cannot be empty.")
        self._api_key = api_key.strip()
        self._model = model
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Call Gemini REST API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self._api_key}"
        parts = []
        if system_prompt:
            parts.append({"text": f"System: {system_prompt}\n\n"})
        parts.append({"text": prompt})

        payload = {"contents": [{"parts": parts}]}
        headers = {"Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code != 200:
                    raise RuntimeError(f"Gemini API error ({response.status_code}): {response.text[:200]}")
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except httpx.RequestError as exc:
            raise RuntimeError(f"Network error communicating with Gemini API: {exc.__class__.__name__}") from None

    async def extract_facts(self, text: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        raw = await self.generate(f"Extract atomic facts from:\n{text}")
        return [{"raw_claim": raw, "confidence": 0.5}]

    async def reason_relationship(
        self,
        fact_a: dict[str, Any],
        fact_b: dict[str, Any],
        evidence_a: str,
        evidence_b: str,
    ) -> dict[str, Any]:
        raw = await self.generate(f"Compare:\nA: {fact_a}\nB: {fact_b}")
        return {"relationship_type": "RELATED", "confidence": 0.5, "reason": raw}
