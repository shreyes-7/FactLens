"""
Unit tests for number parsing, Indian/Western scales, and negative handling.
"""

from backend.app.normalization.numbers import (
    detect_scale_multiplier,
    normalize_number,
    parse_raw_number_string,
)


def test_parse_raw_number_simple():
    val, is_neg = parse_raw_number_string("127.0")
    assert val == 127.0
    assert is_neg is False


def test_parse_raw_number_with_commas():
    val, is_neg = parse_raw_number_string("107,517,088")
    assert val == 107517088.0
    assert is_neg is False


def test_parse_raw_number_parentheses_negative():
    val, is_neg = parse_raw_number_string("(452 Cr)")
    assert val == -452.0
    assert is_neg is True


def test_parse_raw_number_with_currency_symbol():
    val, is_neg = parse_raw_number_string("₹52,350 million")
    assert val == 52350.0
    assert is_neg is False


def test_detect_scale_multiplier():
    assert detect_scale_multiplier("INR Crore") == 1e7
    assert detect_scale_multiplier("Rs. 127 Cr") == 1e7
    assert detect_scale_multiplier("50 Lakh") == 1e5
    assert detect_scale_multiplier("2.5 million") == 1e6
    assert detect_scale_multiplier("1.4 Bn") == 1e9
    assert detect_scale_multiplier("100 percent") == 1.0


def test_normalize_number_crores():
    # 127 Cr -> 1,270,000,000.0
    norm = normalize_number(value_numeric=127.0, unit="INR Crore")
    assert norm == 1270000000.0


def test_normalize_number_parentheses_loss():
    # (452 Cr) -> -4,520,000,000.0
    norm = normalize_number(value_numeric=452.0, raw_value_text="Rs. (452 Cr)", unit="INR Crore")
    assert norm == -4520000000.0


def test_normalize_number_millions():
    # 52,350 million -> 52,350,000,000.0
    norm = normalize_number(value_numeric=52350.0, raw_value_text="₹52,350 million")
    assert norm == 52350000000.0


def test_normalize_number_percentage():
    # 18.0 percent stays 18.0
    norm = normalize_number(value_numeric=18.0, raw_value_text="18%+", unit="percent")
    assert norm == 18.0


def test_normalize_number_compound_scale():
    # 17.34 Lakh Crore -> 17,340,000,000,000.0 (17.34 * 1e12)
    norm = normalize_number(value_numeric=17.34, raw_value_text="Rs. 17.34 Lakh Crore", unit="INR")
    assert norm == 17340000000000.0

