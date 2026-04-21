"""Query parsing helpers for Vietnamese food/promotion questions."""

from __future__ import annotations

import re
import unicodedata

_CATEGORY_ALIASES = {
    "pho": "phở",
    "phở": "phở",
    "com": "cơm",
    "cơm": "cơm",
    "bun": "bún",
    "bún": "bún",
    "do uong": "đồ uống",
    "đồ uống": "đồ uống",
    "nuoc": "đồ uống",
    "nước": "đồ uống",
    "trang mieng": "tráng miệng",
    "tráng miệng": "tráng miệng",
    "che": "tráng miệng",
    "chè": "tráng miệng",
}

_RANGE_RE = re.compile(
    r"(?:tu|từ)\s*(\d+(?:[.,]\d+)?)\s*(k|nghin|nghìn|vnd|d|đ)?\s*(?:den|đến|-)\s*(\d+(?:[.,]\d+)?)\s*(k|nghin|nghìn|vnd|d|đ)?"
)
_MAX_RE = re.compile(
    r"(?:duoi|dưới|toi da|tối đa|<=?)\s*(\d+(?:[.,]\d+)?)\s*(k|nghin|nghìn|vnd|d|đ)?"
)
_MIN_RE = re.compile(
    r"(?:tren|trên|tu|từ|>=?)\s*(\d+(?:[.,]\d+)?)\s*(k|nghin|nghìn|vnd|d|đ)?"
)


def normalize_text(text: str) -> str:
    """Normalize casing and spaces."""
    return " ".join((text or "").strip().lower().split())


def strip_accents(text: str) -> str:
    """Convert Vietnamese text to non-accented form for matching."""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def infer_category(query: str) -> str | None:
    """Infer category keyword from user query when possible."""
    normalized = normalize_text(query)
    normalized_plain = strip_accents(normalized)

    for alias, canonical in _CATEGORY_ALIASES.items():
        alias_plain = strip_accents(alias)
        if alias in normalized or alias_plain in normalized_plain:
            return canonical
    return None


def _to_vnd(number_text: str, unit: str | None) -> int:
    value = float(number_text.replace(",", "."))
    unit_normalized = (unit or "").strip().lower()
    if unit_normalized in {"k", "nghin", "nghìn"}:
        value *= 1000
    return int(value)


def extract_price_bounds(query: str) -> tuple[int | None, int | None]:
    """Extract min/max price (VND) from free-form Vietnamese query."""
    text = normalize_text(strip_accents(query))

    range_match = _RANGE_RE.search(text)
    if range_match:
        min_value = _to_vnd(range_match.group(1), range_match.group(2))
        max_value = _to_vnd(range_match.group(3), range_match.group(4))
        if min_value > max_value:
            min_value, max_value = max_value, min_value
        return min_value, max_value

    min_value: int | None = None
    max_value: int | None = None

    max_match = _MAX_RE.search(text)
    if max_match:
        max_value = _to_vnd(max_match.group(1), max_match.group(2))

    min_match = _MIN_RE.search(text)
    if min_match and not range_match:
        min_value = _to_vnd(min_match.group(1), min_match.group(2))

    if min_value is not None and max_value is not None and min_value > max_value:
        min_value, max_value = max_value, min_value

    return min_value, max_value
