"""Guardrail helpers for data-team scope control."""

from __future__ import annotations

from src.skills.query_skill import normalize_text, strip_accents

_OUT_OF_SCOPE_HINTS = [
    "thoi tiet",
    "chung khoan",
    "bong da",
    "lap trinh",
    "profile",
    "ho so",
    "tai khoan",
    "mat khau",
    "hinh anh",
    "anh mon",
    "photo",
]


def guard_out_of_scope(user_text: str) -> str | None:
    """Return a guardrail response when user intent is outside supported scope."""
    normalized = strip_accents(normalize_text(user_text))
    if not normalized:
        return "Bạn vui lòng nhập nội dung cần tra cứu món ăn hoặc ưu đãi nhé."

    if any(token in normalized for token in _OUT_OF_SCOPE_HINTS):
        return (
            "Mình hiện hỗ trợ tra cứu thực đơn, giá món và ưu đãi theo món. "
            "Bạn hãy gửi câu hỏi theo các nội dung này nhé."
        )

    return None
