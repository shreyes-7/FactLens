"""
Unit tests for date & period normalization.
"""

from datetime import date
from backend.app.normalization.dates import normalize_period


def test_normalize_fiscal_year_short():
    start, end = normalize_period("FY24")
    assert start == date(2023, 4, 1)
    assert end == date(2024, 3, 31)


def test_normalize_fiscal_year_hyphenated():
    start, end = normalize_period("FY2023-24")
    assert start == date(2023, 4, 1)
    assert end == date(2024, 3, 31)

    start2, end2 = normalize_period("2023-24")
    assert start2 == date(2023, 4, 1)
    assert end2 == date(2024, 3, 31)


def test_normalize_fiscal_quarters():
    # Q1 FY24 -> 2023-04-01 to 2023-06-30
    q1_s, q1_e = normalize_period("Q1 FY24")
    assert q1_s == date(2023, 4, 1)
    assert q1_e == date(2023, 6, 30)

    # Q3 FY24 -> 2023-10-01 to 2023-12-31
    q3_s, q3_e = normalize_period("Q3 FY24")
    assert q3_s == date(2023, 10, 1)
    assert q3_e == date(2023, 12, 31)

    # Q4 FY24 -> 2024-01-01 to 2024-03-31
    q4_s, q4_e = normalize_period("Q4 FY24")
    assert q4_s == date(2024, 1, 1)
    assert q4_e == date(2024, 3, 31)


def test_normalize_explicit_date():
    start, end = normalize_period("as of March 31, 2024")
    assert start == date(2024, 3, 31)
    assert end == date(2024, 3, 31)


def test_normalize_calendar_year():
    start, end = normalize_period("2024")
    assert start == date(2024, 1, 1)
    assert end == date(2024, 12, 31)


def test_normalize_empty_period():
    assert normalize_period(None) == (None, None)
    assert normalize_period("") == (None, None)
