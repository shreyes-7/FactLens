"""
Unit tests for FactExtractor orchestration and rejection handling.
"""

from typing import Any
from uuid import uuid4
import pytest

from backend.app.extraction.fact_extractor import FactExtractor
from backend.app.providers.llm.base import LLMProvider


class MockLLM(LLMProvider):
    def __init__(self, response_text: str):
        self.response_text = response_text

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-model"

    async def generate(self, prompt: str, system_prompt: str | None = None, **kwargs) -> str:
        return self.response_text

    async def extract_facts(self, text: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return []

    async def reason_relationship(
        self,
        fact_a: dict[str, Any],
        fact_b: dict[str, Any],
        evidence_a: str,
        evidence_b: str,
    ) -> dict[str, Any]:
        return {}


@pytest.mark.asyncio
async def test_fact_extractor_accepts_grounded_fact():
    chunk_text = "Delhivery recorded full year EBITDA of Rs. 127 Cr in FY24."
    mock_response = """
    {
      "facts": [
        {
          "subject": "Delhivery",
          "predicate": "EBITDA",
          "raw_claim": "Delhivery recorded full year EBITDA of Rs. 127 Cr in FY24.",
          "raw_value_text": "Rs. 127 Cr",
          "value_numeric": 127.0,
          "unit": "INR Crore",
          "fact_type": "NUMERICAL",
          "period_text": "FY24",
          "status": "actual",
          "confidence": 0.95,
          "quote": "EBITDA of Rs. 127 Cr in FY24."
        }
      ]
    }
    """
    extractor = FactExtractor(MockLLM(mock_response))
    accepted, rejected = await extractor.extract_from_chunk(
        chunk_text=chunk_text,
        document_id=uuid4(),
        dataset_id=uuid4(),
        page_id=uuid4(),
        chunk_id=uuid4(),
    )

    assert len(accepted) == 1
    assert rejected == 0
    fact, evidence = accepted[0]
    assert fact.subject == "Delhivery"
    assert fact.value_numeric == 127.0
    assert evidence.quote == "EBITDA of Rs. 127 Cr in FY24."
    assert evidence.start_offset is not None


@pytest.mark.asyncio
async def test_fact_extractor_rejects_hallucinated_quote():
    chunk_text = "Delhivery recorded full year EBITDA of Rs. 127 Cr in FY24."
    mock_response = """
    {
      "facts": [
        {
          "subject": "Delhivery",
          "predicate": "Loss",
          "raw_claim": "Delhivery suffered a loss of 2000 Cr.",
          "value_numeric": -2000.0,
          "fact_type": "NUMERICAL",
          "confidence": 0.9,
          "quote": "Delhivery suffered a massive loss of 2000 Cr in 2020."
        }
      ]
    }
    """
    extractor = FactExtractor(MockLLM(mock_response))
    accepted, rejected = await extractor.extract_from_chunk(
        chunk_text=chunk_text,
        document_id=uuid4(),
        dataset_id=uuid4(),
        page_id=uuid4(),
        chunk_id=uuid4(),
    )

    assert len(accepted) == 0
    assert rejected == 1


@pytest.mark.asyncio
async def test_fact_extractor_handles_invalid_json():
    chunk_text = "Delhivery recorded full year EBITDA of Rs. 127 Cr in FY24."
    mock_response = "I am sorry, I cannot format this as JSON."

    extractor = FactExtractor(MockLLM(mock_response))
    accepted, rejected = await extractor.extract_from_chunk(
        chunk_text=chunk_text,
        document_id=uuid4(),
        dataset_id=uuid4(),
        page_id=uuid4(),
        chunk_id=uuid4(),
    )

    assert len(accepted) == 0
    assert rejected == 0
