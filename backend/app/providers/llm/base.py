"""
LLM Provider Base Interface.
Decouples application and extraction logic from specific LLM vendors.
"""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract interface for all FactLens LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'groq', 'gemini')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Active model identifier."""
        pass

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate a raw text completion."""
        pass

    @abstractmethod
    async def extract_facts(self, text: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Extract candidate facts from chunk text with grounding evidence.
        Returns a list of structured fact dictionaries.
        """
        pass

    @abstractmethod
    async def reason_relationship(
        self,
        fact_a: dict[str, Any],
        fact_b: dict[str, Any],
        evidence_a: str,
        evidence_b: str,
    ) -> dict[str, Any]:
        """
        Reason about the relationship between two candidate facts.
        Returns relationship classification and reasoning rationale.
        """
        pass
