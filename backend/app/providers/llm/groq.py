"""
Groq LLM Provider Implementation.
Primary and default LLM provider using Groq's high-speed hosted inference API.
"""

import asyncio
import json
import logging
from typing import Any
import httpx

from backend.app.providers.llm.base import LLMProvider

logger = logging.getLogger("factlens.llm.groq")


class GroqProvider(LLMProvider):
    """Groq API client implementing LLMProvider."""

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-oss-120b",
        timeout: float = 60.0,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("Groq API key cannot be empty.")
        self._api_key = api_key.strip()
        self._model = model
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Call Groq chat completions API with automatic rate-limit backoff."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 4096,
        }
        if system_prompt and "json" in system_prompt.lower():
            payload["response_format"] = {"type": "json_object"}

        max_retries = 3
        backoff = 3.0

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(self.BASE_URL, headers=headers, json=payload)

                    if response.status_code == 429:
                        if attempt < max_retries:
                            retry_after = float(response.headers.get("retry-after", backoff))
                            logger.warning(
                                f"Groq 429 rate limit hit. Backing off for {retry_after:.1f}s (attempt {attempt + 1}/{max_retries})..."
                            )
                            await asyncio.sleep(retry_after)
                            backoff *= 1.5
                            continue
                        else:
                            error_msg = response.text[:200]
                            raise RuntimeError(f"Groq API rate limit exceeded ({response.status_code}): {error_msg}")

                    if response.status_code != 200:
                        error_msg = response.text[:200]
                        raise RuntimeError(f"Groq API error ({response.status_code}): {error_msg}")

                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except httpx.RequestError as exc:
                if attempt < max_retries:
                    await asyncio.sleep(backoff)
                    continue
                raise RuntimeError(f"Network error communicating with Groq API: {exc.__class__.__name__}") from None


    async def extract_facts(self, text: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Extract candidate facts from text chunk using Groq with structured prompt."""
        system_prompt = (
            "You are FactLens Fact Extraction Engine. Extract atomic, evidence-grounded facts from text. "
            "Output valid JSON array with keys: subject, predicate, raw_claim, value_text, value_numeric, "
            "unit, fact_type (NUMERICAL, SEMANTIC, DERIVED), period_text, quote, confidence (0.0 to 1.0)."
        )
        prompt = f"Extract all atomic verifiable facts from this passage:\n\n{text}\n\nReturn JSON array only."
        response_text = await self.generate(prompt=prompt, system_prompt=system_prompt)
        try:
            # Strip markdown formatting if present
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
            return data if isinstance(data, list) else []
        except Exception:
            return [{"raw_claim": response_text, "confidence": 0.5}]

    async def reason_relationship(
        self,
        fact_a: dict[str, Any],
        fact_b: dict[str, Any],
        evidence_a: str,
        evidence_b: str,
    ) -> dict[str, Any]:
        """Reason about relationship between two facts using Groq."""
        system_prompt = (
            "You are FactLens Relationship Reasoning Engine. Compare two facts and their evidence. "
            "Classify relationship as: CORROBORATES, CONTRADICTS, CONTEXTUAL_DIFFERENCE, RELATED, or UNCERTAIN. "
            "Output JSON with keys: relationship_type, confidence (0.0-1.0), reason."
        )
        prompt = (
            f"Fact A: {json.dumps(fact_a)}\nEvidence A: {evidence_a}\n\n"
            f"Fact B: {json.dumps(fact_b)}\nEvidence B: {evidence_b}\n\n"
            "Analyze whether Fact A and Fact B corroborate, contradict, differ by context, or are merely related."
        )
        response_text = await self.generate(prompt=prompt, system_prompt=system_prompt)
        try:
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except Exception:
            return {
                "relationship_type": "RELATED",
                "confidence": 0.5,
                "reason": response_text,
            }
