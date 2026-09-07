"""
Unit tests for FactNormalizer orchestrator.
"""

from datetime import date
from uuid import uuid4
from backend.app.normalization.normalizer import FactNormalizer
from backend.app.schemas.fact import FactCreate, FactType


def test_fact_normalizer_crores_and_fy():
    fact = FactCreate(
        dataset_id=uuid4(),
        document_id=uuid4(),
        subject="Delhivery",
        predicate="EBITDA",
        raw_claim="FY24 EBITDA increased by Rs. 578 Cr to Rs. 127 Cr",
        value_numeric=127.0,
        raw_value_text="Rs. 127 Cr",
        unit="INR Crore",
        fact_type=FactType.NUMERICAL,
        period_text="FY24",
    )

    norm_fact = FactNormalizer.normalize_fact(fact)
    assert norm_fact.normalized_value_numeric == 1270000000.0
    assert norm_fact.normalized_unit == "INR"
    assert norm_fact.period_start == date(2023, 4, 1)
    assert norm_fact.period_end == date(2024, 3, 31)

    # Verify raw values are completely preserved
    assert norm_fact.value_numeric == 127.0
    assert norm_fact.raw_value_text == "Rs. 127 Cr"
    assert norm_fact.unit == "INR Crore"
    assert norm_fact.period_text == "FY24"


def test_fact_normalizer_dict():
    fact_dict = {
        "value_numeric": 452.0,
        "raw_value_text": "Rs. (452 Cr)",
        "unit": "INR Crore",
        "period_text": "FY23",
    }
    res = FactNormalizer.normalize_dict(fact_dict)
    assert res["normalized_value_numeric"] == -4520000000.0
    assert res["normalized_unit"] == "INR"
    assert res["period_start"] == date(2022, 4, 1)
    assert res["period_end"] == date(2023, 3, 31)
