"""
Resilient Fallback LLM Provider for FactLens.
Attempts primary LLM provider (e.g. Gemini) and transparently falls back to
secondary provider (e.g. Groq) on any API error, rate limit (429), or service outage (503).
"""

import logging
from typing import Any

from backend.app.providers.llm.base import LLMProvider

logger = logging.getLogger("factlens.llm.fallback")


class FallbackLLMProvider(LLMProvider):
    """Wrapper that tries primary provider first, falling back to secondary on failure."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.last_used_provider = primary.provider_name
        self.last_used_model = primary.model_name

    @property
    def provider_name(self) -> str:
        return f"{self.primary.provider_name}_with_{self.fallback.provider_name}_fallback"

    @property
    def model_name(self) -> str:
        return f"{self.primary.model_name} (fallback: {self.fallback.model_name})"

    @property
    def active_provider_name(self) -> str:
        return getattr(self, "last_used_provider", self.primary.provider_name)

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Attempt primary provider; on failure, log and execute with fallback provider."""
        try:
            res = await self.primary.generate(prompt=prompt, system_prompt=system_prompt)
            self.last_used_provider = self.primary.provider_name
            self.last_used_model = self.primary.model_name
            return res
        except Exception as exc:
            logger.warning(
                f"Primary LLM ({self.primary.provider_name} - {self.primary.model_name}) failed: {exc}. "
                f"Falling back to {self.fallback.provider_name} ({self.fallback.model_name})..."
            )
            res = await self.fallback.generate(prompt=prompt, system_prompt=system_prompt)
            self.last_used_provider = self.fallback.provider_name
            self.last_used_model = self.fallback.model_name
            return res

    async def extract_facts(self, text: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        try:
            return await self.primary.extract_facts(text=text, context=context)
        except Exception as exc:
            logger.warning(
                f"Primary extract_facts failed: {exc}. Falling back to {self.fallback.provider_name}..."
            )
            return await self.fallback.extract_facts(text=text, context=context)

    async def reason_relationship(
        self,
        fact_a: dict[str, Any],
        fact_b: dict[str, Any],
        evidence_a: str,
        evidence_b: str,
    ) -> dict[str, Any]:
        try:
            return await self.primary.reason_relationship(
                fact_a=fact_a, fact_b=fact_b, evidence_a=evidence_a, evidence_b=evidence_b
            )
        except Exception as exc:
            logger.warning(
                f"Primary reason_relationship failed: {exc}. Falling back to {self.fallback.provider_name}..."
            )
            return await self.fallback.reason_relationship(
                fact_a=fact_a, fact_b=fact_b, evidence_a=evidence_a, evidence_b=evidence_b
            )
