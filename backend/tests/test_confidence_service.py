"""
Tests for FactConfidenceService (deterministic scoring, positive & negative signals).
"""

import pytest
from backend.app.services.confidence_service import FactConfidenceService


def test_complete_fact_high_confidence():
    fact = {
        "entity": "Delhivery",
        "predicate": "Express Parcel Shipments",
        "raw_value": "740 million",
        "normalized_value_numeric": 740000000.0,
        "unit": "shipments",
        "normalized_unit": "shipments",
        "period_text": "FY24",
        "scope": "Consolidated",
    }
    evidence = {
        "quote": "Express parcel shipment volumes grew to 740 million in FY24 from 680 million in FY23.",
        "page_number": 42,
    }

    result = FactConfidenceService.calculate_confidence(fact, evidence, has_corroboration=True)

    assert result.score >= 90
    assert result.level == "HIGH"
    assert result.level_label == "High Confidence"
    assert result.positive_count >= 5
    assert result.negative_count == 0


def test_missing_period_and_scope_low_confidence():
    fact = {
        "entity": "Delhivery",
        "predicate": "Operating Profit",
        "raw_value": "1200 Cr",
        "normalized_value_numeric": 12000000000.0,
        "unit": "INR",
        # missing period and scope
    }
    evidence = {
        "quote": "Short citation here.",
        "page_number": 10,
    }

    result = FactConfidenceService.calculate_confidence(fact, evidence)

    assert result.score < 90
    assert any("Missing Temporal Period" in s.signal for s in result.signals)
    assert any("Scope Unspecified" in s.signal for s in result.signals)


def test_table_ambiguity_warning_penalty():
    fact = {
        "entity": "Company",
        "predicate": "Revenue",
        "raw_value": "500 Cr",
        "period_text": "FY24",
        "metadata": {
            "table_ambiguity": True,
            "extraction_warning": "Multi-column subtotal overlap detected",
        },
    }
    evidence = {
        "quote": "Subtotal table row value 500 Cr",
        "page_number": 5,
    }

    result = FactConfidenceService.calculate_confidence(fact, evidence)
    assert any("Table Extraction Warning" in s.signal for s in result.signals)
    assert result.score <= 70


def test_score_clamped_between_0_and_100():
    # Extreme negative
    fact = {
        "metadata": {"table_ambiguity": True}
    }
    result_low = FactConfidenceService.calculate_confidence(fact, None)
    assert result_low.score >= 0

    # Extreme positive
    fact_high = {
        "entity": "Delhivery",
        "predicate": "Revenue",
        "raw_value": "8141 Cr",
        "normalized_value_numeric": 81410000000.0,
        "unit": "INR",
        "period_text": "FY24",
        "scope": "Consolidated",
    }
    evidence_high = {
        "quote": "Consolidated revenue from contracts with customers reached ₹8,141 Cr in FY24.",
        "page_number": 12,
    }
    result_high = FactConfidenceService.calculate_confidence(fact_high, evidence_high, has_corroboration=True)
    assert result_high.score <= 100
