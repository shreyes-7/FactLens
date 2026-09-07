"""
Deterministic reasoning engine for FactLens.
Executes high-precision mathematical, unit, and temporal comparisons to resolve
obvious corroborations, contradictions, and contextual period differences.
"""

from datetime import date
from typing import Any

from backend.app.matching.filters import (
    check_metric_compatibility,
    check_predicate_alignment,
    check_temporal_compatibility,
)
from backend.app.schemas.relationship import RelationshipType


def compute_numeric_variance(val_a: float | None, val_b: float | None) -> float | None:
    """
    Calculate relative percentage difference between two scalars.
    Returns float in range [0.0, inf) or None if either value is None.
    e.g., 1,266,410,000 vs 1,270,000,000 -> 0.00282 (0.28%)
    """
    if val_a is None or val_b is None:
        return None

    if val_a == val_b:
        return 0.0

    denom = max(abs(val_a), abs(val_b))
    if denom == 0.0:
        return 0.0

    return abs(val_a - val_b) / denom


def evaluate_deterministic_relationship(
    fact_a: dict[str, Any],
    fact_b: dict[str, Any],
    rounding_tolerance: float = 0.015,  # 1.5% tolerance for corporate reporting rounding
) -> tuple[RelationshipType | None, float, str, dict[str, Any]]:
    """
    Attempt to conclusively resolve relationship using structured rules and math.
    Returns: (relationship_type, confidence, reason, contextual_factors)
    If deterministic rules cannot resolve with high confidence, returns (None, 0.0, "", {}).
    """
    # 1. Temporal comparison
    temporal_ok, temporal_reason = check_temporal_compatibility(fact_a, fact_b)
    pred_aligned, pred_score = check_predicate_alignment(fact_a, fact_b)
    metric_ok, metric_reason = check_metric_compatibility(fact_a, fact_b)

    num_a = fact_a.get("normalized_value_numeric")
    num_b = fact_b.get("normalized_value_numeric")

    # Check status difference (actual vs forecast/projection)
    status_a = (fact_a.get("status") or "actual").lower().strip()
    status_b = (fact_b.get("status") or "actual").lower().strip()
    if status_a != status_b and (status_a in ("forecast", "target", "projection") or status_b in ("forecast", "target", "projection")):
        return (
            RelationshipType.CONTEXTUAL_DIFFERENCE,
            0.92,
            f"Contextual difference in status: one fact reports '{status_a}' while the other represents '{status_b}'.",
            {"status_factor": f"{status_a} vs {status_b}"},
        )

    # 2. Both facts have numerical values
    if num_a is not None and num_b is not None and metric_ok:
        variance = compute_numeric_variance(num_a, num_b)

        # Case A: Same metric, same/overlapping period
        if pred_aligned and temporal_ok and variance is not None:
            if variance <= rounding_tolerance:
                pct = variance * 100
                return (
                    RelationshipType.CORROBORATES,
                    0.96,
                    f"Facts corroborate: normalized values ({num_a:,.1f} vs {num_b:,.1f} {fact_a.get('normalized_unit') or ''}) "
                    f"align within rounding tolerance ({pct:.2f}% delta <= {rounding_tolerance*100:.1f}%) for matching period.",
                    {"variance": round(variance, 5), "temporal_overlap": True},
                )
            elif variance > 0.05:
                # Same period and predicate, but materially different (> 5% delta)
                # Check if scope differs (e.g. Consolidated vs Standalone)
                scope_a = (fact_a.get("scope") or "").lower().strip()
                scope_b = (fact_b.get("scope") or "").lower().strip()
                if scope_a and scope_b and scope_a != scope_b:
                    return (
                        RelationshipType.CONTEXTUAL_DIFFERENCE,
                        0.90,
                        f"Contextual difference in scope: '{scope_a}' vs '{scope_b}' explains the value variance ({variance*100:.1f}%).",
                        {"scope_factor": f"{scope_a} vs {scope_b}", "variance": round(variance, 4)},
                    )
                else:
                    # Clear contradiction
                    return (
                        RelationshipType.CONTRADICTS,
                        0.92,
                        f"Material numeric contradiction: for the same metric ({fact_a.get('predicate')}) and timeframe, "
                        f"values disagree ({num_a:,.1f} vs {num_b:,.1f}) with {variance*100:.1f}% variance without reconciling context.",
                        {"variance": round(variance, 4), "period": fact_a.get("period_text")},
                    )

        # Case B: Same metric, explicitly disjoint timeframes
        if pred_aligned and not temporal_ok and temporal_reason == "disjoint_period_range":
            pt_a = fact_a.get("period_text") or "Period A"
            pt_b = fact_b.get("period_text") or "Period B"
            return (
                RelationshipType.CONTEXTUAL_DIFFERENCE,
                0.95,
                f"Contextual difference: metrics refer to different reporting periods ({pt_a} vs {pt_b}).",
                {"temporal_difference": f"{pt_a} vs {pt_b}"},
            )

    # 3. Different predicates on the same entity
    if not pred_aligned and fact_a.get("subject", "").lower() == fact_b.get("subject", "").lower():
        return (
            RelationshipType.RELATED,
            0.85,
            f"Facts describe the same subject ('{fact_a.get('subject')}') but measure different metrics "
            f"('{fact_a.get('predicate')}' vs '{fact_b.get('predicate')}').",
            {"shared_subject": fact_a.get("subject")},
        )

    # Fallback to LLM for nuanced semantic/contextual reasoning
    return (None, 0.0, "", {})
