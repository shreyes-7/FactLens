"""
Unit tests for evidence grounding verification and offset calculation.
"""

from backend.app.extraction.fact_extractor import locate_quote_in_text


def test_locate_quote_exact_match():
    text = "In FY24, Delhivery achieved full year EBITDA profitability of Rs. 127 Cr."
    quote = "EBITDA profitability of Rs. 127 Cr"
    
    start, end, is_exact = locate_quote_in_text(quote, text)
    assert is_exact is True
    assert start == 38
    assert end == 72
    assert text[start:end] == quote


def test_locate_quote_whitespace_normalized():
    text = "In FY24, Delhivery achieved\nfull year EBITDA profitability\n  of Rs. 127 Cr."
    quote = "full year EBITDA profitability of Rs. 127 Cr."
    
    start, end, is_grounded = locate_quote_in_text(quote, text)
    assert is_grounded is True
    assert start is not None


def test_locate_quote_hallucinated_returns_false():
    text = "In FY24, Delhivery achieved full year EBITDA profitability of Rs. 127 Cr."
    hallucinated_quote = "Delhivery had negative revenue of 500 million."
    
    start, end, is_grounded = locate_quote_in_text(hallucinated_quote, text)
    assert is_grounded is False
    assert start is None
    assert end is None


def test_locate_quote_empty():
    assert locate_quote_in_text("", "Some text") == (None, None, False)
    assert locate_quote_in_text("Some quote", "") == (None, None, False)
