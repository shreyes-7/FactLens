"""
Unit tests for Relationship Reasoning (Phase 07).
Tests deterministic math, temporal/scope reconciliation, LLM contextual reasoning,
and strict canonical ordering constraints.
"""

from datetime import date
from unittest.mock import AsyncMock
from uuid import UUID, uuid4
import pytest

from backend.app.reasoning.deterministic import (
    compute_numeric_variance,
    evaluate_deterministic_relationship,
)
from backend.app.reasoning.relationship_classifier import RelationshipClassifier
from backend.app.schemas.relationship import (
    FactRelationshipBase,
    RelationshipType,
)


def test_compute_numeric_variance():
    # Identical values
    assert compute_numeric_variance(100.0, 100.0) == 0.0

    # Delhivery EBITDA: 1,266.41 Mn vs 127 Cr
    val_annual = 1266.41 * 1e6  # 1,266,410,000.0
    val_pres = 127.0 * 1e7       # 1,270,000,000.0
    variance = compute_numeric_variance(val_annual, val_pres)
    assert variance is not None
    assert round(variance, 4) == 0.0028  # 0.28% variance

    # None and Zero edge cases
    assert compute_numeric_variance(None, 100.0) is None
    assert compute_numeric_variance(0.0, 0.0) == 0.0


def test_evaluate_deterministic_corroboration():
    """Corroboration: values align within rounding tolerance (<1.5%) for identical period."""
    fact_a = {
        "subject": "Delhivery",
        "predicate": "EBITDA",
        "normalized_value_numeric": 1270000000.0,  # 127 Cr
        "normalized_unit": "INR",
        "period_start": date(2023, 4, 1),
        "period_end": date(2024, 3, 31),
        "period_text": "FY24",
    }
    fact_b = {
        "subject": "Delhivery",
        "predicate": "EBITDA",
        "normalized_value_numeric": 1266410000.0,  # 1,266.41 Mn
        "normalized_unit": "INR",
        "period_start": date(2023, 4, 1),
        "period_end": date(2024, 3, 31),
        "period_text": "FY24",
    }

    rel_type, conf, reason, factors = evaluate_deterministic_relationship(fact_a, fact_b)
    assert rel_type == RelationshipType.CORROBORATES
    assert conf >= 0.95
    assert "rounding tolerance" in reason
    assert factors.get("temporal_overlap") is True


def test_evaluate_deterministic_contradiction():
    """Contradiction: materially conflicting figures (>5% delta) for same metric and timeframe."""
    fact_a = {
        "subject": "India",
        "predicate": "GDP growth",
        "normalized_value_numeric": 7.0,
        "normalized_unit": "PERCENT",
        "period_start": date(2024, 4, 1),
        "period_end": date(2025, 3, 31),
        "period_text": "FY25",
        "status": "actual",
    }
    fact_b = {
        "subject": "India",
        "predicate": "GDP growth",
        "normalized_value_numeric": 6.0,
        "normalized_unit": "PERCENT",
        "period_start": date(2024, 4, 1),
        "period_end": date(2025, 3, 31),
        "period_text": "FY25",
        "status": "actual",
    }

    rel_type, conf, reason, factors = evaluate_deterministic_relationship(fact_a, fact_b)
    assert rel_type == RelationshipType.CONTRADICTS
    assert conf >= 0.90
    assert "contradiction" in reason.lower()
    assert factors.get("variance") is not None


def test_evaluate_deterministic_contextual_difference_time():
    """Contextual difference: disparate timeframes (FY23 vs FY24)."""
    fact_a = {
        "subject": "Delhivery",
        "predicate": "EBITDA",
        "normalized_value_numeric": -4520000000.0,  # Loss of (452 Cr)
        "normalized_unit": "INR",
        "period_start": date(2022, 4, 1),
        "period_end": date(2023, 3, 31),
        "period_text": "FY23",
    }
    fact_b = {
        "subject": "Delhivery",
        "predicate": "EBITDA",
        "normalized_value_numeric": 1270000000.0,   # Profit of 127 Cr
        "normalized_unit": "INR",
        "period_start": date(2023, 4, 1),
        "period_end": date(2024, 3, 31),
        "period_text": "FY24",
    }

    rel_type, conf, reason, factors = evaluate_deterministic_relationship(fact_a, fact_b)
    assert rel_type == RelationshipType.CONTEXTUAL_DIFFERENCE
    assert conf >= 0.90
    assert "different reporting periods" in reason
    assert "temporal_difference" in factors


def test_evaluate_deterministic_contextual_difference_scope():
    """Contextual difference: Consolidated vs Standalone perimeter."""
    fact_a = {
        "subject": "Delhivery",
        "predicate": "Revenue",
        "normalized_value_numeric": 50000000000.0,
        "normalized_unit": "INR",
        "period_start": date(2023, 4, 1),
        "period_end": date(2024, 3, 31),
        "scope": "standalone",
    }
    fact_b = {
        "subject": "Delhivery",
        "predicate": "Revenue",
        "normalized_value_numeric": 55000000000.0,
        "normalized_unit": "INR",
        "period_start": date(2023, 4, 1),
        "period_end": date(2024, 3, 31),
        "scope": "consolidated",
    }

    rel_type, conf, reason, factors = evaluate_deterministic_relationship(fact_a, fact_b)
    assert rel_type == RelationshipType.CONTEXTUAL_DIFFERENCE
    assert "scope" in reason.lower()
    assert "scope_factor" in factors


def test_evaluate_deterministic_contextual_difference_status():
    """Contextual difference: Actual results vs Target/Projection."""
    fact_a = {
        "subject": "Delhivery",
        "predicate": "EBITDA margin",
        "normalized_value_numeric": 2.5,
        "normalized_unit": "PERCENT",
        "status": "actual",
    }
    fact_b = {
        "subject": "Delhivery",
        "predicate": "EBITDA margin",
        "normalized_value_numeric": 5.0,
        "normalized_unit": "PERCENT",
        "status": "target",
    }

    rel_type, conf, reason, factors = evaluate_deterministic_relationship(fact_a, fact_b)
    assert rel_type == RelationshipType.CONTEXTUAL_DIFFERENCE
    assert "status" in reason.lower()
    assert "status_factor" in factors


def test_evaluate_deterministic_related():
    """Related: same entity but distinct metrics (EBITDA vs Freight Volume)."""
    fact_a = {
        "subject": "Delhivery",
        "predicate": "EBITDA",
        "normalized_value_numeric": 1270000000.0,
        "normalized_unit": "INR",
    }
    fact_b = {
        "subject": "Delhivery",
        "predicate": "Freight Volume",
        "normalized_value_numeric": 1400000.0,
        "normalized_unit": "METRIC_TON",
    }

    rel_type, conf, reason, _ = evaluate_deterministic_relationship(fact_a, fact_b)
    assert rel_type == RelationshipType.RELATED
    assert "different metrics" in reason


def test_canonical_ordering_validation():
    """Strict constraint: fact_a_id must be strictly less than fact_b_id."""
    id1 = UUID("11111111-1111-1111-1111-111111111111")
    id2 = UUID("22222222-2222-2222-2222-222222222222")

    # Correct ordering
    rel = FactRelationshipBase(
        fact_a_id=id1,
        fact_b_id=id2,
        relationship_type=RelationshipType.CORROBORATES,
        reason="Valid canonical pair",
    )
    assert rel.fact_a_id == id1

    # Inverted ordering must raise ValueError
    with pytest.raises(ValueError, match="strictly less than"):
        FactRelationshipBase(
            fact_a_id=id2,
            fact_b_id=id1,
            relationship_type=RelationshipType.CORROBORATES,
            reason="Invalid inverted pair",
        )


@pytest.mark.asyncio
async def test_relationship_classifier_llm_mocked():
    """Test LLM contextual reasoning flow with mocked response."""
    id1 = "11111111-1111-1111-1111-111111111111"
    id2 = "22222222-2222-2222-2222-222222222222"

    mock_llm = AsyncMock()
    mock_llm.model_name = "mock-llm"
    mock_llm.generate.return_value = """
    {
      "relationship_type": "CORROBORATES",
      "confidence": 0.94,
      "reason": "Both documents report identical FY24 profitability turnaround under Ind-AS.",
      "contextual_factors": {"accounting": "Ind-AS 116"}
    }
    """

    classifier = RelationshipClassifier(llm_provider=mock_llm)

    # Inconclusive facts that defer to LLM
    fact_a = {
        "id": id2,  # deliberately pass in reverse to verify canonical sort
        "subject": "Delhivery",
        "predicate": "Turnaround",
        "raw_claim": "Turned EBITDA positive",
    }
    fact_b = {
        "id": id1,
        "subject": "Delhivery",
        "predicate": "Turnaround",
        "raw_claim": "Achieved positive operational earnings",
    }

    res = await classifier.classify_pair(fact_a, fact_b)
    # Canonical ordering preserved: id1 < id2
    assert str(res.fact_a_id) == id1
    assert str(res.fact_b_id) == id2
    assert res.relationship_type == RelationshipType.CORROBORATES
    assert res.confidence == 0.94
    assert res.reasoning_method == "llm_contextual_reasoning"
