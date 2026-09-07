"""
Unit tests for unit canonicalization.
"""

from backend.app.normalization.units import normalize_unit


def test_normalize_currencies():
    assert normalize_unit("INR Crore") == "INR"
    assert normalize_unit("Rs. Cr") == "INR"
    assert normalize_unit("₹") == "INR"
    assert normalize_unit("Rupees") == "INR"
    assert normalize_unit("USD million") == "USD"
    assert normalize_unit("$") == "USD"
    assert normalize_unit("EUR") == "EUR"


def test_normalize_percentages():
    assert normalize_unit("percent") == "PERCENT"
    assert normalize_unit("%") == "PERCENT"
    assert normalize_unit("percentage") == "PERCENT"
    assert normalize_unit(None, raw_value_text="30%+") == "PERCENT"


def test_normalize_durations():
    assert normalize_unit("days") == "DAYS"
    assert normalize_unit("nwc days") == "DAYS"
    assert normalize_unit("hours") == "HOURS"


def test_normalize_weights_and_shares():
    assert normalize_unit("metric tons") == "METRIC_TON"
    assert normalize_unit("Mn Tons") == "METRIC_TON"
    assert normalize_unit("equity shares") == "SHARES"
    assert normalize_unit("shares") == "SHARES"
    assert normalize_unit("parcels") == "PARCELS"


def test_normalize_basis_points():
    assert normalize_unit("bps") == "BPS"
    assert normalize_unit("basis points") == "BPS"


def test_normalize_custom_unit_fallback():
    assert normalize_unit("pincodes") == "PINCODES"
    assert normalize_unit("automated gateways") == "AUTOMATED GATEWAYS"


def test_normalize_empty():
    assert normalize_unit(None) is None
    assert normalize_unit("") is None

