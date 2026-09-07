"""
Unit Normalization Engine for FactLens.
Standardizes heterogeneous unit strings into canonical representations
(e.g., INR Crore -> INR, % -> PERCENT, metric tons -> METRIC_TON).
"""

import re

# Canonical unit mappings
UNIT_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Indian / Global Currencies
    (re.compile(r"(\b(rs\.?|rupees?|inr)\b|[₹])", re.IGNORECASE), "INR"),
    (re.compile(r"(\b(usd|dollars?)\b|[\$])", re.IGNORECASE), "USD"),
    (re.compile(r"(\b(eur|euros?)\b|[€])", re.IGNORECASE), "EUR"),
    (re.compile(r"(\b(gbp|pounds?)\b|[£])", re.IGNORECASE), "GBP"),

    # Percentages
    (re.compile(r"(\b(percent|percentage|per\s*cent)\b|[%])", re.IGNORECASE), "PERCENT"),


    # Time & Durations
    (re.compile(r"\b(days?|nwc\s*days?)\b", re.IGNORECASE), "DAYS"),
    (re.compile(r"\b(hours?|hrs?)\b", re.IGNORECASE), "HOURS"),
    (re.compile(r"\b(months?|mos?)\b", re.IGNORECASE), "MONTHS"),
    (re.compile(r"\b(years?|yrs?)\b", re.IGNORECASE), "YEARS"),

    # Weight / Volume
    (re.compile(r"\b(metric\s*tons?|tonnes?|tons?)\b", re.IGNORECASE), "METRIC_TON"),
    (re.compile(r"\b(kg|kilograms?)\b", re.IGNORECASE), "KILOGRAM"),

    # Equities & Volumes
    (re.compile(r"\b(shares?|equity\s*shares?)\b", re.IGNORECASE), "SHARES"),
    (re.compile(r"\b(parcels?|packages?|shipments?)\b", re.IGNORECASE), "PARCELS"),
]


def normalize_unit(unit: str | None, raw_value_text: str | None = None) -> str | None:
    """
    Standardize raw unit strings into canonical symbols.
    Examples:
        'INR Crore' -> 'INR'
        'Rs. Cr' -> 'INR'
        '30%+' -> 'PERCENT'
        'days' -> 'DAYS'
        'shares' -> 'SHARES'
    """
    combined = f"{unit or ''} {raw_value_text or ''}".strip()
    if not combined:
        return None

    for pattern, canonical in UNIT_PATTERNS:
        if pattern.search(combined):
            return canonical

    # If no pattern matched, clean and return uppercase single-word unit
    clean_unit = re.sub(r"[^A-Za-z0-9_ ]", "", unit or "").strip().upper()
    return clean_unit if clean_unit else None
