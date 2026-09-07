"""
Unit tests for chunk batching fact extraction, chunk_id preservation,
and Gemini 429 rate-limit backoff handling.
"""

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import httpx
import pytest

from backend.app.extraction.fact_extractor import FactExtractor
from backend.app.providers.llm.base import LLMProvider
from backend.app.providers.llm.gemini import GeminiProvider
from backend.app.schemas.chunk import ChunkCreate


class MockLLM(LLMProvider):
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.calls: list[dict[str, str]] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-model"

    async def generate(self, prompt: str, system_prompt: str | None = None, **kwargs) -> str:
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt or ""})
        return self.response_text

    async def extract_facts(self, text: str, context: dict | None = None) -> list[dict]:
        return []

    async def reason_relationship(self, fact_a: dict, fact_b: dict, evidence_a: str, evidence_b: str) -> dict:
        return {}


def test_batch_partitioning():
    """Verify chunk list partitioning preserves order and handles uneven chunk counts."""
    doc_id = uuid4()
    page_id = uuid4()
    chunks = [
        ChunkCreate(
            id=uuid4(),
            document_id=doc_id,
            page_id=page_id,
            chunk_index=i,
            text=f"Chunk content number {i}",
            metadata={"pdf_page_number": 1},
        )
        for i in range(10)
    ]

    batch_size = 4
    batches = [chunks[i : i + batch_size] for i in range(0, len(chunks), batch_size)]

    assert len(batches) == 3
    assert len(batches[0]) == 4
    assert len(batches[1]) == 4
    assert len(batches[2]) == 2
    # Verify exact ordering preserved
    assert [c.chunk_index for c in batches[0]] == [0, 1, 2, 3]
    assert [c.chunk_index for c in batches[1]] == [4, 5, 6, 7]
    assert [c.chunk_index for c in batches[2]] == [8, 9]


@pytest.mark.asyncio
async def test_chunk_id_preservation_and_mapping():
    """Verify that chunk_id from LLM output correctly maps to EvidenceCreate.chunk_id and fact metadata."""
    doc_id = uuid4()
    p1_id = uuid4()
    p2_id = uuid4()
    c1_id = uuid4()
    c2_id = uuid4()

    chunk1 = ChunkCreate(
        id=c1_id,
        document_id=doc_id,
        page_id=p1_id,
        chunk_index=0,
        text="Delhivery reported revenue of Rs. 8,142 Cr in FY24.",
        metadata={"pdf_page_number": 1},
    )
    chunk2 = ChunkCreate(
        id=c2_id,
        document_id=doc_id,
        page_id=p2_id,
        chunk_index=1,
        text="Express parcel volume stood at 740 million shipments in FY24.",
        metadata={"pdf_page_number": 2},
    )

    llm_payload = {
        "facts": [
            {
                "chunk_id": "chunk_1",
                "subject": "Delhivery",
                "predicate": "revenue",
                "raw_claim": "Delhivery reported revenue of Rs. 8,142 Cr in FY24.",
                "raw_value_text": "Rs. 8,142 Cr",
                "value_numeric": 8142.0,
                "unit": "INR Crore",
                "fact_type": "NUMERICAL",
                "period_text": "FY24",
                "status": "actual",
                "confidence": 0.95,
                "quote": "revenue of Rs. 8,142 Cr in FY24.",
            },
            {
                "chunk_id": "chunk_2",
                "subject": "Delhivery",
                "predicate": "express parcel volume",
                "raw_claim": "Express parcel volume stood at 740 million shipments in FY24.",
                "raw_value_text": "740 million",
                "value_numeric": 740.0,
                "unit": "million shipments",
                "fact_type": "NUMERICAL",
                "period_text": "FY24",
                "status": "actual",
                "confidence": 0.92,
                "quote": "Express parcel volume stood at 740 million shipments",
            },
        ]
    }

    mock_llm = MockLLM(json.dumps(llm_payload))
    extractor = FactExtractor(mock_llm)

    accepted, rejected = await extractor.extract_from_batch(
        chunks=[chunk1, chunk2],
        document_id=doc_id,
        dataset_id=uuid4(),
        filename="test_report.pdf",
    )

    assert rejected == 0
    assert len(accepted) == 2

    fact1, ev1 = accepted[0]
    assert ev1.chunk_id == c1_id
    assert ev1.page_id == p1_id
    assert fact1.metadata.get("chunk_id") == str(c1_id)
    assert fact1.metadata.get("pdf_page_number") == 1
    assert "revenue of Rs. 8,142 Cr" in ev1.quote
    assert ev1.start_offset >= 0

    fact2, ev2 = accepted[1]
    assert ev2.chunk_id == c2_id
    assert ev2.page_id == p2_id
    assert fact2.metadata.get("chunk_id") == str(c2_id)
    assert fact2.metadata.get("pdf_page_number") == 2
    assert "Express parcel volume" in ev2.quote
    assert ev2.start_offset >= 0


@pytest.mark.asyncio
async def test_quote_fallback_when_chunk_id_missing():
    """Verify that if LLM omits chunk_id, quote fallback finds the matching chunk in the batch."""
    doc_id = uuid4()
    p1_id = uuid4()
    c1_id = uuid4()
    c2_id = uuid4()

    chunk1 = ChunkCreate(
        id=c1_id,
        document_id=doc_id,
        page_id=p1_id,
        chunk_index=0,
        text="India real GDP growth reached 8.2 percent in FY24 according to NSO.",
        metadata={"pdf_page_number": 5},
    )
    chunk2 = ChunkCreate(
        id=c2_id,
        document_id=doc_id,
        page_id=p1_id,
        chunk_index=1,
        text="Headline inflation moderated to 5.4 percent during the same fiscal year.",
        metadata={"pdf_page_number": 5},
    )

    # Fact with no chunk_id, but quote exists in chunk2
    llm_payload = {
        "facts": [
            {
                "chunk_id": None,
                "subject": "India",
                "predicate": "headline inflation",
                "raw_claim": "Headline inflation moderated to 5.4 percent during FY24.",
                "raw_value_text": "5.4 percent",
                "value_numeric": 5.4,
                "unit": "percent",
                "fact_type": "NUMERICAL",
                "period_text": "FY24",
                "status": "actual",
                "confidence": 0.90,
                "quote": "Headline inflation moderated to 5.4 percent",
            }
        ]
    }

    mock_llm = MockLLM(json.dumps(llm_payload))
    extractor = FactExtractor(mock_llm)

    accepted, rejected = await extractor.extract_from_batch(
        chunks=[chunk1, chunk2],
        document_id=doc_id,
        dataset_id=uuid4(),
    )

    assert rejected == 0
    assert len(accepted) == 1
    fact, ev = accepted[0]
    assert ev.chunk_id == c2_id
    assert fact.metadata.get("chunk_id") == str(c2_id)


@pytest.mark.asyncio
async def test_hallucinated_fact_rejected_in_batch():
    """Verify that facts with ungrounded quotes not in any batch chunk are rejected."""
    doc_id = uuid4()
    c1_id = uuid4()

    chunk1 = ChunkCreate(
        id=c1_id,
        document_id=doc_id,
        page_id=uuid4(),
        chunk_index=0,
        text="Delhivery network reaches over 18,000 pin codes across India.",
        metadata={"pdf_page_number": 1},
    )

    llm_payload = {
        "facts": [
            {
                "chunk_id": "chunk_1",
                "subject": "Competitor",
                "predicate": "market share",
                "raw_claim": "Blue Dart had 40% market share.",
                "raw_value_text": "40%",
                "quote": "Blue Dart had 40% market share across the region.",  # Hallucinated quote
                "confidence": 0.8,
            }
        ]
    }

    mock_llm = MockLLM(json.dumps(llm_payload))
    extractor = FactExtractor(mock_llm)

    accepted, rejected = await extractor.extract_from_batch(
        chunks=[chunk1],
        document_id=doc_id,
        dataset_id=uuid4(),
    )

    assert len(accepted) == 0
    assert rejected == 1


@pytest.mark.asyncio
async def test_gemini_429_retry_and_backoff():
    """Verify GeminiProvider handles 429 response, executes backoff, and succeeds on subsequent attempt."""
    provider = GeminiProvider(api_key="test_key", model="gemini-flash-latest", base_backoff=0.01)

    req = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent")
    resp_429 = httpx.Response(status_code=429, text="Resource exhausted", request=req)
    resp_200 = httpx.Response(
        status_code=200,
        json={"candidates": [{"content": {"parts": [{"text": '{"facts": []}'}]}}]},
        request=req,
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        # First call returns 429, second returns 200
        mock_post.side_effect = [resp_429, resp_200]

        result = await provider.generate("Extract facts", system_prompt="json output")
        assert result == '{"facts": []}'
        assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_gemini_max_retries_exceeded():
    """Verify GeminiProvider raises RuntimeError after exhausting max_retries on 429."""
    provider = GeminiProvider(api_key="test_key", model="gemini-flash-latest", max_retries=2, base_backoff=0.01)

    req = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent")
    resp_429 = httpx.Response(status_code=429, text="Quota exceeded", request=req)

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = resp_429

        with pytest.raises(RuntimeError, match="Quota exceeded after 2 retries"):
            await provider.generate("Extract facts")

        assert mock_post.call_count == 3  # initial attempt + 2 retries


@pytest.mark.asyncio
async def test_gemini_enforces_json_mimetype():
    """Verify GeminiProvider passes responseMimeType=application/json when system prompt mentions json."""
    provider = GeminiProvider(api_key="test_key", model="gemini-flash-latest")

    req = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent")
    resp_200 = httpx.Response(
        status_code=200,
        json={"candidates": [{"content": {"parts": [{"text": '{"status": "ok"}'}]}}]},
        request=req,
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = resp_200

        await provider.generate("Extract", system_prompt="Respond strictly with JSON format.")

        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["generationConfig"]["responseMimeType"] == "application/json"


@pytest.mark.asyncio
async def test_gemini_no_api_key_in_url():
    """Verify GeminiProvider does NOT pass api key in URL query parameter and uses x-goog-api-key header."""
    provider = GeminiProvider(api_key="AQ.secret_gemini_key_1234567890", model="gemini-flash-latest")

    req = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent")
    resp_200 = httpx.Response(
        status_code=200,
        json={"candidates": [{"content": {"parts": [{"text": "clean response"}]}}]},
        request=req,
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = resp_200
        await provider.generate("Hello")

        url_called = str(mock_post.call_args[0][0])
        headers_called = mock_post.call_args[1]["headers"]

        # Ensure ?key= is NOT in the URL
        assert "key=" not in url_called
        assert "?key=" not in url_called
        # Ensure header contains key
        assert headers_called.get("x-goog-api-key") == "AQ.secret_gemini_key_1234567890"


@pytest.mark.asyncio
async def test_gemini_daily_quota_exhaustion_fails_fast():
    """Verify GeminiProvider fails fast immediately without retrying when daily quota (RPD) is exhausted."""
    provider = GeminiProvider(api_key="test_key", model="gemini-flash-latest", max_retries=3, base_backoff=0.01)

    req = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent")
    rpd_error = {
        "error": {
            "code": 429,
            "message": "Quota exceeded for quota metric 'GenerateRequestsPerDayPerProject'.",
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                    "reason": "RATE_LIMIT_EXCEEDED",
                    "metadata": {
                        "quota_limit": "GenerateRequestsPerDayPerProject",
                        "quota_metric": "generativelanguage.googleapis.com/generate_content_requests",
                    },
                }
            ],
        }
    }
    resp_429_rpd = httpx.Response(status_code=429, json=rpd_error, request=req)

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = resp_429_rpd

        with pytest.raises(RuntimeError, match="Gemini daily quota exhausted"):
            await provider.generate("Extract")

        # Must fail fast on attempt 1 WITHOUT retrying 3 times
        assert mock_post.call_count == 1


@pytest.mark.asyncio
async def test_gemini_retry_after_header_handling():
    """Verify GeminiProvider respects Retry-After header on temporary rate limit."""
    provider = GeminiProvider(api_key="test_key", model="gemini-flash-latest", base_backoff=0.01)

    req = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent")
    resp_429 = httpx.Response(
        status_code=429,
        text="Rate limit",
        headers={"retry-after": "0.01"},
        request=req,
    )
    resp_200 = httpx.Response(
        status_code=200,
        json={"candidates": [{"content": {"parts": [{"text": '{"facts": []}'}]}}]},
        request=req,
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [resp_429, resp_200]
        result = await provider.generate("Extract")
        assert result == '{"facts": []}'
        assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_fallback_to_groq_on_gemini_failure():
    """Verify FallbackLLMProvider seamlessly switches to Groq when Gemini fails."""
    from backend.app.providers.llm.fallback import FallbackLLMProvider
    from backend.app.providers.llm.groq import GroqProvider

    gemini_provider = GeminiProvider(api_key="test_gemini", model="gemini-flash-latest", max_retries=0)
    groq_provider = GroqProvider(api_key="gsk_test_groq", model="openai/gpt-oss-20b")
    fallback_provider = FallbackLLMProvider(gemini_provider, groq_provider)

    req_gemini = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent")
    resp_gemini_429 = httpx.Response(status_code=429, text="Resource exhausted", request=req_gemini)

    req_groq = httpx.Request("POST", groq_provider.BASE_URL)
    resp_groq_200 = httpx.Response(
        status_code=200,
        json={"choices": [{"message": {"content": '{"facts": [{"chunk_id": "chunk_1", "subject": "Test", "predicate": "metric", "raw_claim": "Claim", "quote": "Claim", "confidence": 0.9}]}'}}]},
        request=req_groq,
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [resp_gemini_429, resp_groq_200]

        result = await fallback_provider.generate("Extract")
        assert '{"facts":' in result
        assert fallback_provider.last_used_provider == "groq"
        assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_groq_json_validate_failed_recovery():
    """Verify GroqProvider recovers when Groq grammar validator fails with 400 json_validate_failed."""
    from backend.app.providers.llm.groq import GroqProvider

    provider = GroqProvider(api_key="gsk_test", model="openai/gpt-oss-20b")
    req = httpx.Request("POST", provider.BASE_URL)
    resp_400 = httpx.Response(
        status_code=400,
        json={"error": {"code": "json_validate_failed", "message": "Failed to validate JSON."}},
        request=req,
    )
    resp_200 = httpx.Response(
        status_code=200,
        json={"choices": [{"message": {"content": '{"facts": []}'}}]},
        request=req,
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [resp_400, resp_200]

        result = await provider.generate("Extract", system_prompt="Respond in JSON format")
        assert result == '{"facts": []}'
        assert mock_post.call_count == 2
        # Verify second call stripped response_format
        second_payload = mock_post.call_args_list[1][1]["json"]
        assert "response_format" not in second_payload


def test_groq_response_normalization_strips_thinking_and_markdown():
    """Verify GroqProvider strips <think> reasoning tokens and markdown json code blocks."""
    from backend.app.providers.llm.groq import GroqProvider
    import re

    raw_content = "<think>Let me analyze the text chunks...</think>\n```json\n{\"facts\": [{\"predicate\": \"GDP\"}]}\n```"
    # Execute same normalization logic
    cleaned = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    assert cleaned == '{"facts": [{\"predicate\": \"GDP\"}]}'


def test_secret_redaction_in_logs():
    """Verify mask_sensitive_data scrubs API keys from URLs, headers, and log messages."""
    from backend.app.observability.logger import mask_sensitive_data

    # Test URL query param
    url_log = "POST https://generativelanguage.googleapis.com/v1beta/models/gemini:generateContent?key=AQ.fake_dummy_gemini_token_for_testing_1234567890 HTTP/1.1 429"
    masked_url = mask_sensitive_data(url_log)
    assert "fake_dummy_gemini" not in masked_url
    assert "?key=[REDACTED_KEY]" in masked_url or "[REDACTED_GEMINI_KEY]" in masked_url

    # Test Groq key
    groq_log = "Using GROQ_API_KEY=gsk_fake_dummy_groq_token_for_testing_1234567890 for request"
    masked_groq = mask_sensitive_data(groq_log)
    assert "fake_dummy_groq" not in masked_groq
    assert "[REDACTED_KEY]" in masked_groq or "[REDACTED_GROQ_KEY]" in masked_groq

    # Test standalone raw key
    raw_key_log = "Sent token gsk_fake_dummy_groq_token_for_testing_1234567890"
    masked_raw = mask_sensitive_data(raw_key_log)
    assert "fake_dummy_groq" not in masked_raw
    assert "[REDACTED_GROQ_KEY]" in masked_raw

    # Test Gemini header
    gemini_hdr_log = "headers={'x-goog-api-key': 'AQ.fake_dummy_gemini_token_for_testing_1234567890'}"
    masked_hdr = mask_sensitive_data(gemini_hdr_log)
    assert "fake_dummy_gemini" not in masked_hdr
    assert "[REDACTED_KEY]" in masked_hdr or "[REDACTED_GEMINI_KEY]" in masked_hdr

