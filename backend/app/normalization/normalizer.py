"""
Fact Normalization Orchestrator for FactLens.
Applies number scaling, unit canonicalization, and date range parsing
to FactCreate objects and dictionaries.
"""

from typing import Any
from backend.app.normalization.dates import normalize_period
from backend.app.normalization.numbers import normalize_number
from backend.app.normalization.units import normalize_unit
from backend.app.schemas.fact import FactCreate


class FactNormalizer:
    """Orchestrates multi-dimensional fact normalization."""

    @staticmethod
    def normalize_fact(fact: FactCreate) -> FactCreate:
        """
        Normalize a FactCreate object in place, setting:
          - normalized_value_numeric
          - normalized_unit
          - period_start
          - period_end
        """
        # 1. Normalize number & scale
        norm_val = normalize_number(
            value_numeric=fact.value_numeric,
            raw_value_text=fact.raw_value_text,
            unit=fact.unit,
        )
        fact.normalized_value_numeric = norm_val

        # 2. Normalize unit
        norm_unit = normalize_unit(unit=fact.unit, raw_value_text=fact.raw_value_text)
        fact.normalized_unit = norm_unit

        # 3. Normalize temporal bounds
        p_start, p_end = normalize_period(fact.period_text)
        if p_start and not fact.period_start:
            fact.period_start = p_start
        if p_end and not fact.period_end:
            fact.period_end = p_end

        return fact

    @staticmethod
    def normalize_dict(fact_dict: dict[str, Any]) -> dict[str, Any]:
        """Normalize a raw dictionary representation of a fact."""
        norm_val = normalize_number(
            value_numeric=fact_dict.get("value_numeric"),
            raw_value_text=fact_dict.get("raw_value_text"),
            unit=fact_dict.get("unit"),
        )
        norm_unit = normalize_unit(
            unit=fact_dict.get("unit"),
            raw_value_text=fact_dict.get("raw_value_text"),
        )
        p_start, p_end = normalize_period(fact_dict.get("period_text"))

        fact_dict["normalized_value_numeric"] = norm_val
        fact_dict["normalized_unit"] = norm_unit
        if p_start and not fact_dict.get("period_start"):
            fact_dict["period_start"] = p_start
        if p_end and not fact_dict.get("period_end"):
            fact_dict["period_end"] = p_end

        return fact_dict
