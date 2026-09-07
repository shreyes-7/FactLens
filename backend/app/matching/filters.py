"""
Structured candidate filters for FactLens.
Enforces hard architectural rules: dataset boundaries, non-self checks,
cross-document preferences, metric/unit compatibility, and temporal overlap.
"""

from datetime import date
import re
from typing import Any


def check_dataset_boundary(fact_a: dict[str, Any], fact_b: dict[str, Any]) -> bool:
    """Facts must belong to the same dataset."""
    d_a = str(fact_a.get("dataset_id") or "")
    d_b = str(fact_b.get("dataset_id") or "")
    return bool(d_a and d_b and d_a == d_b)


def check_non_self(fact_a: dict[str, Any], fact_b: dict[str, Any]) -> bool:
    """Cannot match a fact with itself."""
    id_a = str(fact_a.get("id") or "")
    id_b = str(fact_b.get("id") or "")
    return bool(id_a and id_b and id_a != id_b)


def check_cross_document(fact_a: dict[str, Any], fact_b: dict[str, Any]) -> bool:
    """Check if facts originate from different source documents."""
    doc_a = str(fact_a.get("document_id") or "")
    doc_b = str(fact_b.get("document_id") or "")
    return bool(doc_a and doc_b and doc_a != doc_b)


def check_temporal_compatibility(fact_a: dict[str, Any], fact_b: dict[str, Any]) -> tuple[bool, str]:
    """
    Check whether two facts share or overlap in reporting timeframe.
    Returns (is_compatible, reason).
    """
    start_a = fact_a.get("period_start")
    end_a = fact_a.get("period_end")
    start_b = fact_b.get("period_start")
    end_b = fact_b.get("period_end")

    # If both have explicit date ranges
    if start_a and end_a and start_b and end_b:
        # Convert strings to date objects if necessary
        if isinstance(start_a, str):
            start_a = date.fromisoformat(start_a)
        if isinstance(end_a, str):
            end_a = date.fromisoformat(end_a)
        if isinstance(start_b, str):
            start_b = date.fromisoformat(start_b)
        if isinstance(end_b, str):
            end_b = date.fromisoformat(end_b)

        # Overlap check
        overlap = max(start_a, start_b) <= min(end_a, end_b)
        if overlap:
            if start_a == start_b and end_a == end_b:
                return True, "identical_period_range"
            return True, "overlapping_period_range"
        return False, "disjoint_period_range"

    # Fallback to period_text comparison
    pt_a = (fact_a.get("period_text") or "").strip().lower()
    pt_b = (fact_b.get("period_text") or "").strip().lower()

    if pt_a and pt_b:
        if pt_a == pt_b:
            return True, "identical_period_text"
        # Substring or FY matching e.g. "fy24" in "fy2023-24"
        if ("fy" in pt_a and "fy" in pt_b) and (pt_a[-2:] == pt_b[-2:]):
            return True, "compatible_fiscal_year"

    # If one or both is unspecified, don't rule out pairing
    return True, "unspecified_period"


def check_metric_compatibility(fact_a: dict[str, Any], fact_b: dict[str, Any]) -> tuple[bool, str]:
    """
    Check if the metrics/units can be mathematically compared.
    e.g. INR vs INR (compatible), PERCENT vs PERCENT (compatible),
         INR vs METRIC_TON (incompatible for direct value comparison).
    """
    u_a = fact_a.get("normalized_unit") or fact_a.get("unit")
    u_b = fact_b.get("normalized_unit") or fact_b.get("unit")

    # If both have normalized units
    if u_a and u_b:
        if u_a.upper() == u_b.upper():
            return True, f"identical_unit_{u_a.upper()}"
        # Cross-currency compatibility (e.g. INR and USD are both financial, but need conversion)
        currencies = {"INR", "USD", "EUR", "GBP"}
        if u_a.upper() in currencies and u_b.upper() in currencies:
            return True, "currency_conversion_needed"
        return False, f"incompatible_units_{u_a}_vs_{u_b}"

    # Semantic facts without units can still be compared
    if fact_a.get("fact_type") == "SEMANTIC" or fact_b.get("fact_type") == "SEMANTIC":
        return True, "semantic_fact"

    return True, "unit_unspecified"


def check_predicate_alignment(fact_a: dict[str, Any], fact_b: dict[str, Any]) -> tuple[bool, float]:
    """
    Lexical and token check for predicate alignment.
    e.g. 'EBITDA' vs 'EBITDA' -> 1.0
         'Revenue' vs 'Revenue from operations' -> high match
    """
    pred_a = (fact_a.get("predicate") or "").lower().strip()
    pred_b = (fact_b.get("predicate") or "").lower().strip()

    if not pred_a or not pred_b:
        return False, 0.0

    if pred_a == pred_b:
        return True, 1.0

    tokens_a = set(re.findall(r"\w+", pred_a))
    tokens_b = set(re.findall(r"\w+", pred_b))

    if not tokens_a or not tokens_b:
        return False, 0.0

    jaccard = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
    is_aligned = jaccard >= 0.3 or (tokens_a.issubset(tokens_b) or tokens_b.issubset(tokens_a))
    return is_aligned, jaccard


def is_candidate_pair(
    fact_a: dict[str, Any],
    fact_b: dict[str, Any],
    require_cross_document: bool = True,
) -> tuple[bool, list[str]]:
    """
    Evaluate all structured filters to determine if two facts form an eligible candidate pair.
    Returns (is_eligible, match_reasons).
    """
    reasons: list[str] = []

    # 1. Dataset boundary
    if not check_dataset_boundary(fact_a, fact_b):
        return False, ["different_datasets"]

    # 2. Non-self check
    if not check_non_self(fact_a, fact_b):
        return False, ["self_fact"]

    # 3. Cross-document check (if required)
    if require_cross_document and not check_cross_document(fact_a, fact_b):
        return False, ["same_document"]

    if check_cross_document(fact_a, fact_b):
        reasons.append("cross_document")

    # 4. Metric compatibility
    metric_ok, metric_reason = check_metric_compatibility(fact_a, fact_b)
    if not metric_ok:
        return False, [metric_reason]
    reasons.append(metric_reason)

    # 5. Temporal compatibility
    temporal_ok, temporal_reason = check_temporal_compatibility(fact_a, fact_b)
    if temporal_ok:
        reasons.append(temporal_reason)

    # 6. Predicate alignment
    pred_ok, pred_score = check_predicate_alignment(fact_a, fact_b)
    if pred_ok:
        reasons.append(f"predicate_aligned_{pred_score:.2f}")

    return True, reasons
