from __future__ import annotations
import re

_PHONE_RE = re.compile(r"^[\+\d][\d\s\-\(\)]{6,18}\d$")


def validate_phone(text: str) -> str | None:
    """
    Returns normalised phone string or None if invalid.
    Accepts formats: +7 999 123-45-67, 8(999)123-45-67, etc.
    """
    cleaned = text.strip()
    if _PHONE_RE.match(cleaned):
        return cleaned
    return None


def validate_name(text: str) -> str | None:
    name = text.strip()
    if 2 <= len(name) <= 64:
        return name
    return None


def validate_time(text: str) -> bool:
    """Validate HH:MM format."""
    text = text.strip()
    if len(text) != 5 or text[2] != ":":
        return False
    try:
        h, m = int(text[:2]), int(text[3:])
        return 0 <= h <= 23 and 0 <= m <= 59
    except ValueError:
        return False


def validate_date(text: str) -> bool:
    """Validate YYYY-MM-DD format."""
    from datetime import date
    try:
        date.fromisoformat(text.strip())
        return True
    except ValueError:
        return False
