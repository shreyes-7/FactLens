"""
Date & Period Normalization Engine for FactLens.
Normalizes Indian fiscal years (FY24, FY2023-24), fiscal quarters (Q1-Q4),
calendar years, and explicit reporting dates into ISO (start_date, end_date) ranges.
"""

from datetime import date
import re


def parse_two_digit_year(yy: int) -> int:
    """Convert two-digit year (e.g. 24) to 2024."""
    if yy < 100:
        return 2000 + yy if yy < 70 else 1900 + yy
    return yy


def normalize_period(period_text: str | None) -> tuple[date | None, date | None]:
    """
    Parse textual temporal descriptors into explicit date bounds.
    Indian Fiscal Year convention: April 1 of (year - 1) to March 31 of year.
    Examples:
        'FY24' -> (date(2023, 4, 1), date(2024, 3, 31))
        'FY2023-24' -> (date(2023, 4, 1), date(2024, 3, 31))
        'Q3 FY24' -> (date(2023, 10, 1), date(2023, 12, 31))
        'March 31, 2024' -> (date(2024, 3, 31), date(2024, 3, 31))
        '2024' -> (date(2024, 1, 1), date(2024, 12, 31))
    """
    if not period_text:
        return None, None

    text = period_text.strip()

    # 1. Fiscal Quarter: e.g. Q1 FY24, Q3 FY2024, Q4 2024
    quarter_match = re.search(r"\bQ([1-4])\s*(?:FY)?\s*(\d{2,4})\b", text, re.IGNORECASE)
    if quarter_match:
        q_num = int(quarter_match.group(1))
        end_year = parse_two_digit_year(int(quarter_match.group(2)))
        start_year = end_year - 1

        if q_num == 1:
            return date(start_year, 4, 1), date(start_year, 6, 30)
        elif q_num == 2:
            return date(start_year, 7, 1), date(start_year, 9, 30)
        elif q_num == 3:
            return date(start_year, 10, 1), date(start_year, 12, 31)
        elif q_num == 4:
            return date(end_year, 1, 1), date(end_year, 3, 31)

    # 2. Fiscal Year hyphenated: e.g. FY2023-24, 2023-24, FY 2023-2024
    fy_hyphen_match = re.search(r"(?:FY\s*)?(\d{4})[-/](\d{2,4})", text, re.IGNORECASE)
    if fy_hyphen_match:
        start_yr = int(fy_hyphen_match.group(1))
        end_yr_part = int(fy_hyphen_match.group(2))
        end_yr = parse_two_digit_year(end_yr_part) if end_yr_part < 100 else end_yr_part
        return date(start_yr, 4, 1), date(end_yr, 3, 31)

    # 3. Single Fiscal Year: e.g. FY24, FY 2024
    fy_single_match = re.search(r"\bFY\s*(\d{2,4})\b", text, re.IGNORECASE)
    if fy_single_match:
        end_yr = parse_two_digit_year(int(fy_single_match.group(1)))
        start_yr = end_yr - 1
        return date(start_yr, 4, 1), date(end_yr, 3, 31)

    # 4. Explicit date: e.g. March 31, 2024 or 31 March 2024
    explicit_date_match = re.search(
        r"(?:as\s*of\s*|year\s*ended\s*)?(?:(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s*(\d{4}))",
        text,
        re.IGNORECASE,
    )
    if explicit_date_match:
        month_name = explicit_date_match.group(1).lower()
        day = int(explicit_date_match.group(2))
        year = int(explicit_date_match.group(3))
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        }
        m = months.get(month_name, 1)
        d = date(year, m, day)
        return d, d

    # 5. Calendar Year: e.g. 2024, CY2024, CY24
    cy_match = re.search(r"\b(?:CY\s*)?(\d{4})\b", text, re.IGNORECASE)
    if cy_match:
        yr = int(cy_match.group(1))
        return date(yr, 1, 1), date(yr, 12, 31)

    return None, None
