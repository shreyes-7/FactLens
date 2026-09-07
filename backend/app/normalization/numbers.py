"""
Numerical Normalization Engine for FactLens.
Normalizes heterogeneous numerical formats, Indian scales (Crore, Lakh),
Western scales (Million, Billion), financial parentheses negatives, and currency symbols.
"""

import re
from typing import Any

# Scale multipliers
SCALE_MULTIPLIERS: dict[str, float] = {
    "crore": 1e7,
    "crores": 1e7,
    "cr": 1e7,
    "crs": 1e7,
    "lakh": 1e5,
    "lakhs": 1e5,
    "lac": 1e5,
    "lacs": 1e5,
    "million": 1e6,
    "millions": 1e6,
    "mn": 1e6,
    "m": 1e6,
    "billion": 1e9,
    "billions": 1e9,
    "bn": 1e9,
    "b": 1e9,
    "trillion": 1e12,
    "trillions": 1e12,
    "tn": 1e12,
    "thousand": 1e3,
    "thousands": 1e3,
    "k": 1e3,
}


def parse_raw_number_string(text: str) -> tuple[float | None, bool]:
    """
    Extract raw float scalar and negative flag from a formatted number string.
    Handles parentheses like '(452 Cr)', unicode minus '−', commas '107,517,088', and percentages.
    """
    if not text:
        return None, False

    cleaned = text.strip()
    is_negative = False

    # Check for financial parenthesis notation: (452 Cr) or Rs. (452 Cr)
    if re.search(r"\([^)]*\d+[^)]*\)", cleaned):
        is_negative = True
        # Extract content inside parentheses
        p_match = re.search(r"\(([^)]+)\)", cleaned)
        if p_match:
            cleaned = p_match.group(1)
    elif cleaned.startswith("-") or cleaned.startswith("−"):
        is_negative = True
        cleaned = cleaned[1:].strip()

    # Strip currency symbols and common prefixes
    cleaned = re.sub(r"[₹\$€£]|Rs\.?|INR|USD|EUR", "", cleaned, flags=re.IGNORECASE).strip()


    # Search for first valid number substring (including decimal and commas)
    match = re.search(r"[-+]?\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?", cleaned)
    if not match:
        return None, is_negative

    num_str = match.group(0).replace(",", "")
    try:
        val = float(num_str)
        if is_negative and val > 0:
            val = -val
        return val, is_negative
    except ValueError:
        return None, is_negative


def detect_scale_multiplier(text: str) -> float:
    """
    Detect numerical scale multiplier from words or abbreviations in text or unit string.
    Supports compound scales like 'lakh crore' (1e5 * 1e7 = 1e12) and 'thousand crore' (1e10).
    Avoids duplicate multiplication from synonyms across unit and raw text (e.g. 'crore' and 'cr').
    e.g. 'Rs. 127 Cr' -> 10,000,000 (1e7)
         'Rs. 18.2 Lakh Crore' -> 1,000,000,000,000 (1e12)
    """
    if not text:
        return 1.0

    lower_text = text.lower()

    # 1. Check for known Indian compound scales
    if re.search(r"\b(lakh|lac|lakhs|lacs)\s*(crore|crores|cr|crs)\b", lower_text):
        return 1e12
    if re.search(r"\b(thousand|thousands|k)\s*(crore|crores|cr|crs)\b", lower_text):
        return 1e10

    # 2. Check for single scale multiplier
    tokens = re.findall(r"[A-Za-z]+", lower_text)
    for token in tokens:
        if token in SCALE_MULTIPLIERS:
            return SCALE_MULTIPLIERS[token]

    return 1.0


def normalize_number(
    value_numeric: float | None = None,
    raw_value_text: str | None = None,
    unit: str | None = None,
) -> float | None:
    """
    Calculate the canonical scaled numeric value.
    Example:
        value_numeric=127.0, unit='INR Crore' -> 1,270,000,000.0
        value_numeric=-452.0, unit='INR Crore' -> -4,520,000,000.0
        raw_value_text='107,517,088 shares' -> 107,517,088.0
        value_numeric=18.0, unit='percent' -> 18.0
    """
    # 1. Determine base scalar
    scalar = value_numeric
    is_neg = False

    if raw_value_text:
        parsed_scalar, is_neg = parse_raw_number_string(raw_value_text)
        if scalar is None:
            scalar = parsed_scalar
        elif is_neg and scalar > 0:
            scalar = -scalar

    if scalar is None:
        return None

    # 2. Check for multiplier in unit or raw text
    combined_context = f"{unit or ''} {raw_value_text or ''}"
    multiplier = detect_scale_multiplier(combined_context)

    # Note: If value_numeric was already huge (e.g. 52350000000), don't multiply again
    if multiplier > 1.0 and abs(scalar) < 1e9:
        normalized = scalar * multiplier
    else:
        normalized = scalar

    return float(normalized)
