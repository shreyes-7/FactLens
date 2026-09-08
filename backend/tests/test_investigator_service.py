"""
Tests for ContradictionInvestigatorService (multi-factor audit, variance, contextual differences, true contradictions).
"""

import pytest
from backend.app.services.investigator_service import ContradictionInvestigatorService


def test_investigate_corroboration():
    fact_a = {
        "entity": "Delhivery Limited",
        "predicate": "Express Parcel Shipments",
        "raw_value": "740M",
        "normalized_value": 740000000.0,
        "unit": "shipments",
        "time_period": "FY24",
        "scope": "Consolidated",
        "document_filename": "Annual Report 2024",
        "page_number": 42,
    }
    fact_b = {
        "entity": "Delhivery",
        "predicate": "Express Parcel Shipments",
        "raw_value": "740 million",
        "normalized_value": 740000000.0,
        "unit": "shipments",
        "time_period": "FY24",
        "scope": "Consolidated",
        "document_filename": "Earnings Presentation Q4 FY24",
        "page_number": 15,
    }

    result = ContradictionInvestigatorService.investigate(fact_a, fact_b)

    assert result.verdict_type in ("CORROBORATED", "UNIT_DIFFERENCE")
    assert result.relationship == "CORROBORATES"
    assert result.checks.entity_match is True
    assert result.checks.predicate_match is True
    assert result.checks.period_match is True
    assert result.checks.scope_match is True
    assert result.variance_percent == 0.0
    assert result.review_required is False


def test_investigate_contextual_difference_scope():
    fact_a = {
        "entity": "Delhivery",
        "predicate": "Revenue",
        "raw_value": "₹8,141 Cr",
        "normalized_value": 81410000000.0,
        "unit": "INR",
        "time_period": "FY24",
        "scope": "Consolidated",
        "document_filename": "Annual Report 2024",
        "page_number": 47,
    }
    fact_b = {
        "entity": "Delhivery",
        "predicate": "Revenue",
        "raw_value": "₹7,800 Cr",
        "normalized_value": 78000000000.0,
        "unit": "INR",
        "time_period": "FY24",
        "scope": "Standalone",
        "document_filename": "Prospectus 2024",
        "page_number": 32,
    }

    result = ContradictionInvestigatorService.investigate(fact_a, fact_b)

    assert result.verdict_type == "CONTEXTUAL_DIFFERENCE"
    assert result.checks.scope_match is False
    assert result.checks.period_match is True
    assert "scope" in result.explanation.lower()
    assert result.variance_percent is not None
    assert result.review_required is False


def test_investigate_temporal_progression_not_contradiction():
    fact_a = {
        "entity": "Delhivery",
        "predicate": "Revenue",
        "raw_value": "₹7,800 Cr",
        "normalized_value": 78000000000.0,
        "unit": "INR",
        "time_period": "FY23",
        "scope": "Consolidated",
    }
    fact_b = {
        "entity": "Delhivery",
        "predicate": "Revenue",
        "raw_value": "₹8,141 Cr",
        "normalized_value": 81410000000.0,
        "unit": "INR",
        "time_period": "FY24",
        "scope": "Consolidated",
    }

    result = ContradictionInvestigatorService.investigate(fact_a, fact_b)

    assert result.verdict_type == "TEMPORAL_DIFFERENCE"
    assert result.checks.period_match is False
    assert "temporal progression" in result.verdict.lower() or "fy23" in result.explanation.lower()


def test_investigate_true_contradiction():
    fact_a = {
        "entity": "Delhivery",
        "predicate": "Adjusted EBITDA",
        "raw_value": "₹1,280 Cr",
        "normalized_value": 12800000000.0,
        "unit": "INR",
        "time_period": "FY24",
        "scope": "Consolidated",
    }
    fact_b = {
        "entity": "Delhivery",
        "predicate": "Adjusted EBITDA",
        "raw_value": "₹940 Cr",
        "normalized_value": 9400000000.0,
        "unit": "INR",
        "time_period": "FY24",
        "scope": "Consolidated",
    }

    result = ContradictionInvestigatorService.investigate(fact_a, fact_b)

    assert result.verdict_type == "TRUE_CONTRADICTION"
    assert result.relationship == "CONTRADICTS"
    assert result.checks.period_match is True
    assert result.checks.scope_match is True
    assert result.review_required is True
    assert result.variance_percent is not None
    assert abs(result.variance_percent) > 1.5
