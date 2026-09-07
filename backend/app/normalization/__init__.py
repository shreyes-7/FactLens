"""
FactLens Normalization Package.
Provides number scaling, unit canonicalization, date range parsing, and fact normalization.
"""

from backend.app.normalization.dates import normalize_period
from backend.app.normalization.normalizer import FactNormalizer
from backend.app.normalization.numbers import normalize_number
from backend.app.normalization.units import normalize_unit

__all__ = [
    "FactNormalizer",
    "normalize_number",
    "normalize_unit",
    "normalize_period",
]
