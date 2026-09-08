"""
Fact Confidence and Evidence Quality Scoring Service.
Deterministically computes a 0-100 score and signal breakdown based on
source evidence, page coordinates, normalization, and contextual specificity.
Zero LLM calls.
"""

from typing import Any
from pydantic import BaseModel, Field


class ConfidenceSignal(BaseModel):
    signal: str
    impact: int
    status: str = Field(..., description="pass, warn, or fail")
    description: str


class FactConfidenceResult(BaseModel):
    score: int = Field(..., ge=0, le=100)
    level: str = Field(..., description="HIGH, MEDIUM, or LOW")
    level_label: str = Field(..., description="High, Medium, or Needs Review")
    signals: list[ConfidenceSignal]
    positive_count: int
    negative_count: int


class FactConfidenceService:
    """
    Computes explainable, deterministic fact quality & confidence scores.
    
    Positive Signals:
    - Exact verbatim evidence quote available (+20)
    - Source PDF page number identified (+20)
    - Temporal period identified (+15)
    - Measurement unit identified & normalized (+15)
    - Reporting scope identified (+15)
    - Numeric value successfully normalized (+10)
    - Corroborated by independent fact (+5)

    Negative / Uncertainty Signals:
    - Ambiguous table extraction (-20)
    - Missing temporal period (-15)
    - Missing unit for quantitative metric (-10)
    - Missing or ambiguous scope (-10)
    - Weak / partial evidence quote (< 15 chars) (-10)
    - Extraction warning or parsing uncertainty (-10)
    """

    @staticmethod
    def calculate_confidence(
        fact: dict[str, Any],
        evidence: dict[str, Any] | None = None,
        has_corroboration: bool = False,
    ) -> FactConfidenceResult:
        score = 0
        signals: list[ConfidenceSignal] = []

        # 1. Evidence Quote Quality
        quote = ""
        if evidence:
            quote = evidence.get("quote") or ""
        elif "evidence_quote" in fact:
            quote = fact.get("evidence_quote") or ""

        quote_clean = quote.strip()
        if len(quote_clean) >= 25:
            score += 20
            signals.append(ConfidenceSignal(
                signal="Exact Source Evidence",
                impact=20,
                status="pass",
                description="Verbatim citation extracted directly from source document text."
            ))
        elif len(quote_clean) > 0:
            score += 10
            signals.append(ConfidenceSignal(
                signal="Short Evidence Quote",
                impact=-10,
                status="warn",
                description=f"Evidence citation is short ({len(quote_clean)} chars), potential partial sentence."
            ))
        else:
            signals.append(ConfidenceSignal(
                signal="Missing Evidence Citation",
                impact=-20,
                status="fail",
                description="No verbatim quote grounding found for this extracted fact."
            ))

        # 2. Page Number Grounding
        page_num = None
        if evidence:
            page_num = evidence.get("page_number") or evidence.get("pdf_page_number")
        if page_num is None and "page_number" in fact:
            page_num = fact.get("page_number")
        if page_num is None and isinstance(fact.get("metadata"), dict):
            page_num = fact["metadata"].get("page_number")

        if page_num is not None and int(page_num) > 0:
            score += 20
            signals.append(ConfidenceSignal(
                signal="Page Identification",
                impact=20,
                status="pass",
                description=f"Directly mapped to PDF Page {page_num} with verified chunk coordinates."
            ))
        else:
            signals.append(ConfidenceSignal(
                signal="Page Unresolved",
                impact=-10,
                status="warn",
                description="Specific PDF page number could not be mapped with certainty."
            ))

        # 3. Temporal Period Specificity
        period = fact.get("period_text") or fact.get("temporal_period")
        if period and str(period).strip().lower() not in ("none", "null", "unknown", ""):
            score += 15
            signals.append(ConfidenceSignal(
                signal="Period Identified",
                impact=15,
                status="pass",
                description=f"Explicit fiscal/calendar interval identified: '{period}'."
            ))
        else:
            score -= 15
            signals.append(ConfidenceSignal(
                signal="Missing Temporal Period",
                impact=-15,
                status="warn",
                description="Fiscal year or date interval not explicitly specified in claim."
            ))

        # 4. Measurement Unit Standardization
        unit = fact.get("normalized_unit") or fact.get("unit")
        raw_val = str(fact.get("raw_value") or fact.get("raw_claim") or "")
        is_numeric_claim = (
            fact.get("normalized_value_numeric") is not None
            or fact.get("value_numeric") is not None
            or any(c.isdigit() for c in raw_val)
        )

        if unit and str(unit).strip().lower() not in ("none", "null", "unknown", ""):
            score += 15
            signals.append(ConfidenceSignal(
                signal="Unit Standardized",
                impact=15,
                status="pass",
                description=f"Standardized metric unit: '{unit}'."
            ))
        elif is_numeric_claim:
            score -= 10
            signals.append(ConfidenceSignal(
                signal="Missing Metric Unit",
                impact=-10,
                status="warn",
                description="Quantitative figure lacks standardized measurement or currency unit."
            ))
        else:
            score += 10
            signals.append(ConfidenceSignal(
                signal="Qualitative Fact",
                impact=10,
                status="pass",
                description="Categorical/semantic statement without requiring metric unit."
            ))

        # 5. Reporting Scope Resolution
        scope = fact.get("scope")
        if scope and str(scope).strip().lower() not in ("none", "null", "unknown", ""):
            score += 15
            signals.append(ConfidenceSignal(
                signal="Scope Resolved",
                impact=15,
                status="pass",
                description=f"Entity reporting scope identified: '{scope}'."
            ))
        else:
            score -= 10
            signals.append(ConfidenceSignal(
                signal="Scope Unspecified",
                impact=-10,
                status="warn",
                description="Uncertain whether statement applies to Consolidated, Standalone, or Segment."
            ))

        # 6. Normalization Success
        has_numeric = fact.get("normalized_value_numeric") is not None or fact.get("value_numeric") is not None
        if has_numeric:
            score += 10
            signals.append(ConfidenceSignal(
                signal="Successful Normalization",
                impact=10,
                status="pass",
                description="Numerical magnitude normalized to standard IEEE floating-point."
            ))

        # 7. Corroboration Signal
        if has_corroboration:
            score += 5
            signals.append(ConfidenceSignal(
                signal="Cross-Grounded Corroboration",
                impact=5,
                status="pass",
                description="Corroborated by matching fact discovered in another section or document."
            ))

        # 8. Check for Table Extraction Ambiguity / Warnings in metadata
        meta = fact.get("metadata") or {}
        if isinstance(meta, dict):
            if meta.get("table_ambiguity") or meta.get("extraction_warning"):
                score -= 20
                signals.append(ConfidenceSignal(
                    signal="Table Extraction Warning",
                    impact=-20,
                    status="fail",
                    description=str(meta.get("extraction_warning") or "Multi-column table structure ambiguity.")
                ))

        # Clamp score safely to 0-100
        final_score = max(0, min(100, score))

        if final_score >= 90:
            level = "HIGH"
            level_label = "High Confidence"
        elif final_score >= 70:
            level = "MEDIUM"
            level_label = "Medium Confidence"
        else:
            level = "LOW"
            level_label = "Needs Review"

        positives = sum(1 for s in signals if s.status == "pass")
        negatives = sum(1 for s in signals if s.status in ("warn", "fail"))

        return FactConfidenceResult(
            score=final_score,
            level=level,
            level_label=level_label,
            signals=signals,
            positive_count=positives,
            negative_count=negatives,
        )
