"""
Contradiction Investigator Service.
Performs deterministic multi-factor audits on fact comparisons to explain WHY two facts differ.
Evaluates entity, metric, period, currency, unit, and scope alignment,
and classifies the discrepancy into:
- Verified Corroboration
- Contextual Difference (e.g. Consolidated vs Standalone)
- Temporal Progression (e.g. FY23 vs FY24 trend)
- Unit / Scale Representation Alignment
- True / Unresolved Contradiction
Zero LLM calls.
"""

from typing import Any
from pydantic import BaseModel, Field


class InvestigationChecks(BaseModel):
    entity_match: bool
    predicate_match: bool
    period_match: bool
    currency_match: bool
    unit_match: bool
    scope_match: bool
    same_document: bool
    same_page: bool


class InvestigationResult(BaseModel):
    relationship: str
    verdict: str
    verdict_type: str = Field(
        ...,
        description="CORROBORATED, CONTEXTUAL_DIFFERENCE, TEMPORAL_DIFFERENCE, UNIT_DIFFERENCE, TRUE_CONTRADICTION, or INCOMPARABLE"
    )
    explanation: str
    variance_percent: float | None = None
    absolute_difference: float | None = None
    checks: InvestigationChecks
    confidence: int = Field(..., ge=0, le=100)
    review_required: bool
    metric_name: str
    value_a_display: str
    value_b_display: str
    source_a: dict[str, Any]
    source_b: dict[str, Any]


class ContradictionInvestigatorService:
    """
    Deterministic contradiction & discrepancy investigator.
    Does not make LLM calls; reuses extracted & normalized facts.
    """

    @staticmethod
    def _clean_str(val: Any) -> str:
        if val is None:
            return ""
        s = str(val).strip().lower()
        return "" if s in ("none", "null", "unknown", "n/a") else s

    @classmethod
    def investigate(
        cls,
        fact_a: dict[str, Any],
        fact_b: dict[str, Any],
        existing_rel: dict[str, Any] | None = None,
    ) -> InvestigationResult:
        """
        Run exhaustive deterministic consistency checks between Fact A and Fact B.
        """
        # 1. Entity / Subject Check
        subj_a = cls._clean_str(fact_a.get("entity") or fact_a.get("subject"))
        subj_b = cls._clean_str(fact_b.get("entity") or fact_b.get("subject"))
        # Match if identical or one contains the other (e.g. "delhivery" in "delhivery limited")
        entity_match = bool(subj_a and subj_b and (subj_a in subj_b or subj_b in subj_a or subj_a == subj_b))

        # 2. Metric / Predicate Check
        pred_a = cls._clean_str(fact_a.get("predicate"))
        pred_b = cls._clean_str(fact_b.get("predicate"))
        predicate_match = bool(pred_a and pred_b and (pred_a == pred_b or pred_a in pred_b or pred_b in pred_a))

        # 3. Temporal Period Check
        period_a = cls._clean_str(fact_a.get("time_period") or fact_a.get("period_text"))
        period_b = cls._clean_str(fact_b.get("time_period") or fact_b.get("period_text"))
        period_match = bool(period_a and period_b and (period_a == period_b))

        # 4. Scope Check (Consolidated vs Standalone)
        scope_a = cls._clean_str(fact_a.get("scope"))
        scope_b = cls._clean_str(fact_b.get("scope"))
        scope_match = bool(scope_a == scope_b or (not scope_a and not scope_b))

        # 5. Unit & Currency Check
        unit_a = cls._clean_str(fact_a.get("unit") or fact_a.get("normalized_unit"))
        unit_b = cls._clean_str(fact_b.get("unit") or fact_b.get("normalized_unit"))
        unit_match = bool(unit_a == unit_b or (not unit_a and not unit_b))

        # Determine if INR / USD currency
        is_curr_a = any(c in unit_a for c in ("inr", "rs", "₹", "rupee", "usd", "$", "eur", "€"))
        is_curr_b = any(c in unit_b for c in ("inr", "rs", "₹", "rupee", "usd", "$", "eur", "€"))
        currency_match = (is_curr_a == is_curr_b)

        # 6. Document & Page Check
        doc_a = fact_a.get("document_filename") or fact_a.get("document_id") or ""
        doc_b = fact_b.get("document_filename") or fact_b.get("document_id") or ""
        same_document = bool(doc_a and doc_b and doc_a == doc_b)

        page_a = fact_a.get("page_number") or fact_a.get("fa_page_number")
        page_b = fact_b.get("page_number") or fact_b.get("fb_page_number")
        same_page = bool(same_document and page_a is not None and page_b is not None and page_a == page_b)

        checks = InvestigationChecks(
            entity_match=entity_match,
            predicate_match=predicate_match,
            period_match=period_match,
            currency_match=currency_match,
            unit_match=unit_match,
            scope_match=scope_match,
            same_document=same_document,
            same_page=same_page,
        )

        # 7. Numeric Variance Calculation
        num_a = fact_a.get("normalized_value") or fact_a.get("normalized_value_numeric") or fact_a.get("value_numeric")
        num_b = fact_b.get("normalized_value") or fact_b.get("normalized_value_numeric") or fact_b.get("value_numeric")

        variance_pct: float | None = None
        abs_diff: float | None = None

        if num_a is not None and num_b is not None:
            try:
                fa_float = float(num_a)
                fb_float = float(num_b)
                abs_diff = round(fb_float - fa_float, 4)
                if abs(fa_float) > 1e-9:
                    variance_pct = round(((fb_float - fa_float) / abs(fa_float)) * 100, 2)
                elif abs(fb_float) > 1e-9:
                    variance_pct = 100.0
                else:
                    variance_pct = 0.0
            except (ValueError, TypeError):
                variance_pct = None

        # Format display values
        val_a_disp = str(fact_a.get("raw_value") or fact_a.get("raw_claim") or num_a or "N/A")
        val_b_disp = str(fact_b.get("raw_value") or fact_b.get("raw_claim") or num_b or "N/A")
        metric_name = fact_a.get("predicate") or fact_b.get("predicate") or "Metric"

        # 8. Verdict & Explanation Synthesis
        # Check for Corroboration first
        is_close_variance = variance_pct is not None and abs(variance_pct) <= 1.5
        is_identical_raw = cls._clean_str(val_a_disp) == cls._clean_str(val_b_disp)

        if (is_close_variance or is_identical_raw) and (period_match or not period_a or not period_b):
            if not unit_match and unit_a and unit_b:
                verdict_type = "UNIT_DIFFERENCE"
                verdict = "Scale / Unit Representation Match"
                relationship = "CORROBORATES"
                explanation = (
                    f"Both sources convey the same underlying figure ({val_a_disp} vs {val_b_disp}). "
                    f"Differences reflect unit formatting ('{unit_a}' vs '{unit_b}')."
                )
                confidence = 96
                review_required = False
            else:
                verdict_type = "CORROBORATED"
                verdict = "Verified Corroboration"
                relationship = "CORROBORATES"
                explanation = (
                    f"Claims align within rounding tolerance ({variance_pct:+.2f}% delta <= 1.5%). "
                    f"Both documents report concordant figures for {metric_name}."
                    if variance_pct is not None else
                    f"Identical semantic claims corroborated across documents for {metric_name}."
                )
                confidence = 98
                review_required = False

        elif not period_match and period_a and period_b:
            verdict_type = "TEMPORAL_DIFFERENCE"
            verdict = "Temporal Progression (Not a Contradiction)"
            relationship = "CONTEXTUAL_DIFFERENCE"
            explanation = (
                f"The figures represent distinct time intervals: {period_a.upper()} vs {period_b.upper()}. "
                f"This variance ({variance_pct:+.2f}%) reflects financial/operational progression over time, "
                f"not an erroneous reporting contradiction."
            )
            confidence = 94
            review_required = False

        elif not scope_match and (scope_a or scope_b):
            verdict_type = "CONTEXTUAL_DIFFERENCE"
            verdict = "Contextual Scope Difference"
            relationship = "CONTEXTUAL_DIFFERENCE"
            scope_desc_a = scope_a.capitalize() if scope_a else "Unspecified Scope"
            scope_desc_b = scope_b.capitalize() if scope_b else "Unspecified Scope"
            explanation = (
                f"The variance ({variance_pct:+.2f}%) is explained by reporting scope divergence: "
                f"{scope_desc_a} vs {scope_desc_b}. Financial metrics naturally vary between "
                f"subsidiary/standalone operations and group-wide consolidated accounts."
            )
            confidence = 97
            review_required = False

        elif variance_pct is not None and abs(variance_pct) > 1.5 and period_match and scope_match:
            verdict_type = "TRUE_CONTRADICTION"
            verdict = "Unresolved Material Contradiction"
            relationship = "CONTRADICTS"
            explanation = (
                f"Material divergence of {variance_pct:+.2f}% detected for the same metric ({metric_name}), "
                f"same period ({period_a.upper() or 'Matching'}), and same reporting scope. "
                f"Discrepancy warrants audit verification between source filings."
            )
            confidence = 93
            review_required = True

        else:
            # Contextual or related difference
            verdict_type = "CONTEXTUAL_DIFFERENCE"
            verdict = "Contextual Variance"
            relationship = existing_rel.get("relationship_type", "CONTEXTUAL_DIFFERENCE") if existing_rel else "CONTEXTUAL_DIFFERENCE"
            explanation = (
                f"Discrepancy of {variance_pct:+.2f}% detected. Differing context, terminology, or definitions "
                f"distinguish the two claims."
                if variance_pct is not None else
                "Semantic or contextual variance between claims."
            )
            confidence = 88
            review_required = False

        return InvestigationResult(
            relationship=relationship,
            verdict=verdict,
            verdict_type=verdict_type,
            explanation=explanation,
            variance_percent=variance_pct,
            absolute_difference=abs_diff,
            checks=checks,
            confidence=confidence,
            review_required=review_required,
            metric_name=metric_name,
            value_a_display=val_a_disp,
            value_b_display=val_b_disp,
            source_a={
                "document": doc_a,
                "page": page_a,
                "value": val_a_disp,
                "raw_claim": fact_a.get("raw_claim") or val_a_disp,
                "quote": fact_a.get("evidence_quote") or fact_a.get("quote"),
                "scope": fact_a.get("scope"),
                "period": fact_a.get("time_period") or fact_a.get("period_text"),
                "unit": fact_a.get("unit") or fact_a.get("normalized_unit"),
                "fact_id": str(fact_a.get("id") or fact_a.get("fact_id") or ""),
            },
            source_b={
                "document": doc_b,
                "page": page_b,
                "value": val_b_disp,
                "raw_claim": fact_b.get("raw_claim") or val_b_disp,
                "quote": fact_b.get("evidence_quote") or fact_b.get("quote"),
                "scope": fact_b.get("scope"),
                "period": fact_b.get("time_period") or fact_b.get("period_text"),
                "unit": fact_b.get("unit") or fact_b.get("normalized_unit"),
                "fact_id": str(fact_b.get("id") or fact_b.get("fact_id") or ""),
            },
        )
