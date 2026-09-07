import asyncio
import json
import logging
import random
import re
from typing import Any
import httpx

from backend.app.providers.llm.base import LLMProvider

logger = logging.getLogger("factlens.llm.gemini")


class GeminiProvider(LLMProvider):
    """Google Gemini API provider with rate-limit backoff and structured output support."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-flash-latest",
        timeout: float = 60.0,
        max_retries: int = 3,
        base_backoff: float = 2.0,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("Gemini API key cannot be empty.")
        self._api_key = api_key.strip()
        self._model = model.strip()
        self._timeout = timeout
        self._max_retries = max_retries
        self._base_backoff = base_backoff

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Call Gemini generateContent API with rate-limit retry, exponential backoff, and JSON handling."""
        # Send API key via x-goog-api-key header instead of query parameter to prevent leaking in logs/traces
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"

        gen_config: dict[str, Any] = {
            "temperature": 0.0,
        }
        if system_prompt and "json" in system_prompt.lower():
            gen_config["responseMimeType"] = "application/json"

        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": gen_config,
        }

        if system_prompt:
            payload["system_instruction"] = {
                "parts": [{"text": system_prompt}]
            }

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }

        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(url, headers=headers, json=payload)

                    if response.status_code == 429:
                        quota_metric: str | None = None
                        quota_limit: str | None = None
                        quota_id: str | None = None
                        limit_val: str | None = None
                        retry_delay: float | None = None
                        status_str: str = "RESOURCE_EXHAUSTED"
                        err_msg: str = ""

                        try:
                            err_data = response.json()
                            err_obj = err_data.get("error", {})
                            status_str = err_obj.get("status", "RESOURCE_EXHAUSTED")
                            err_msg = err_obj.get("message", "")
                            details = err_obj.get("details", [])
                            for d in details:
                                if isinstance(d, dict):
                                    type_str = d.get("@type", "")
                                    if "ErrorInfo" in type_str:
                                        meta = d.get("metadata", {})
                                        quota_metric = meta.get("quota_metric")
                                        quota_limit = meta.get("quota_limit")
                                        quota_id = meta.get("quota_location") or meta.get("consumer")
                                        limit_val = meta.get("quota_limit_value")
                                    elif "RetryInfo" in type_str:
                                        r_delay_str = d.get("retryDelay")
                                        if r_delay_str and isinstance(r_delay_str, str):
                                            try:
                                                retry_delay = float(r_delay_str.rstrip("s"))
                                            except ValueError:
                                                pass
                        except Exception:
                            err_msg = response.text[:200]

                        # Check header fallback for retry-after
                        if retry_delay is None:
                            hdr_val = response.headers.get("retry-after")
                            if hdr_val:
                                try:
                                    retry_delay = float(hdr_val)
                                except (ValueError, TypeError):
                                    pass

                        # Determine if this is a daily quota exhaustion (RPD)
                        is_daily = False
                        if quota_limit and any(k in quota_limit.lower() for k in ["perday", "day", "rpd"]):
                            is_daily = True
                        if "per day" in err_msg.lower():
                            is_daily = True

                        if is_daily:
                            logger.warning(
                                f"Gemini 429: Daily quota exhausted [metric={quota_metric}, limit={quota_limit}, "
                                f"status={status_str}]. Failing fast to fallback without retrying."
                            )
                            raise RuntimeError(
                                f"Gemini daily quota exhausted (RPD): metric={quota_metric}, limit={quota_limit}. "
                                "Failing fast to secondary provider."
                            )

                        # Determine quota type
                        quota_type = (
                            "RPM"
                            if quota_limit and "minute" in quota_limit.lower()
                            else "TPM"
                            if quota_limit and "token" in quota_limit.lower()
                            else "TEMPORARY_429"
                        )

                        if attempt < self._max_retries:
                            if retry_delay is not None:
                                backoff = retry_delay + random.uniform(0.5, 1.5)
                            else:
                                backoff = self._base_backoff * (2 ** attempt) + random.uniform(0.5, 1.5)

                            logger.warning(
                                f"Gemini 429 rate limit hit [type={quota_type}, metric={quota_metric}, "
                                f"limit={quota_limit or limit_val}, status={status_str}]. "
                                f"Backing off for {backoff:.1f}s (attempt {attempt + 1}/{self._max_retries})..."
                            )
                            await asyncio.sleep(backoff)
                            continue

                        raise RuntimeError(
                            f"Gemini API error (429 - {quota_type}): Quota exceeded after {self._max_retries} retries: "
                            f"metric={quota_metric}, limit={quota_limit or limit_val}, status={status_str}"
                        )

                    if response.status_code != 200:
                        raise RuntimeError(f"Gemini API error ({response.status_code}): {response.text[:200]}")

                    data = response.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise RuntimeError(f"Gemini returned empty candidates: {data}")

                    text = candidates[0]["content"]["parts"][0]["text"]

                    # Strip markdown json code fences if present: ```json ... ```
                    text = text.strip()
                    if text.startswith("```json"):
                        text = text[7:]
                    elif text.startswith("```"):
                        text = text[3:]
                    if text.endswith("```"):
                        text = text[:-3]

                    return text.strip()

            except httpx.RequestError as exc:
                if attempt < self._max_retries:
                    backoff = self._base_backoff * (2 ** attempt) + random.uniform(0.2, 1.0)
                    logger.warning(
                        f"Gemini network error ({exc.__class__.__name__}). Retrying in {backoff:.1f}s (attempt {attempt + 1}/{self._max_retries})..."
                    )
                    await asyncio.sleep(backoff)
                    continue

                raise RuntimeError(
                    f"Network error communicating with Gemini API after {self._max_retries} retries: {exc.__class__.__name__}"
                ) from None

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
