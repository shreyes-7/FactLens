"""
Unit tests for Fact and Evidence Pydantic schemas.
"""

from datetime import date
from uuid import uuid4
import pytest
from pydantic import ValidationError

from backend.app.schemas.evidence import EvidenceCreate
from backend.app.schemas.fact import FactCreate, FactType


def test_fact_create_valid_numerical():
    fact = FactCreate(
        dataset_id=uuid4(),
        document_id=uuid4(),
        subject="Delhivery",
        predicate="EBITDA",
        raw_claim="Delhivery reported Rs. 127 Cr EBITDA in FY24.",
        value_numeric=127.0,
        raw_value_text="Rs. 127 Cr",
        unit="INR Crore",
        fact_type=FactType.NUMERICAL,
        period_text="FY24",
        confidence=0.95,
    )
    assert fact.subject == "Delhivery"
    assert fact.value_numeric == 127.0
    assert fact.confidence == 0.95


def test_fact_create_requires_value():
    with pytest.raises(ValidationError):
        FactCreate(
            dataset_id=uuid4(),
            document_id=uuid4(),
            subject="Delhivery",
            predicate="Status",
            raw_claim="Some statement without any value field populated",
            confidence=0.9,
        )


def test_fact_create_validates_confidence_range():
    with pytest.raises(ValidationError):
        FactCreate(
            dataset_id=uuid4(),
            document_id=uuid4(),
            subject="Delhivery",
            predicate="Metric",
            raw_claim="Claim",
            value_text="Valid",
            confidence=1.5,  # Invalid: > 1.0
        )


def test_fact_create_validates_period_dates():
    with pytest.raises(ValidationError):
        FactCreate(
            dataset_id=uuid4(),
            document_id=uuid4(),
            subject="India",
            predicate="GDP",
            raw_claim="Claim",
            value_numeric=6.5,
            period_start=date(2025, 4, 1),
            period_end=date(2024, 3, 31),  # Invalid: end < start
        )


def test_evidence_create_valid():
    ev = EvidenceCreate(
        fact_id=uuid4(),
        document_id=uuid4(),
        page_id=uuid4(),
        quote="Delhivery reported Rs. 127 Cr EBITDA in FY24.",
        start_offset=10,
        end_offset=56,
        extraction_confidence=0.95,
    )
    assert ev.quote.startswith("Delhivery")
    assert ev.start_offset == 10
    assert ev.end_offset == 56


def test_evidence_create_validates_offsets():
    with pytest.raises(ValidationError):
        EvidenceCreate(
            fact_id=uuid4(),
            document_id=uuid4(),
            page_id=uuid4(),
            quote="Some quote",
            start_offset=100,
            end_offset=50,  # Invalid: end < start
        )
