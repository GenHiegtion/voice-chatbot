"""Context helpers for tool execution."""

from __future__ import annotations

import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

_session_id_var: ContextVar[str] = ContextVar("tool_session_id", default="")
_current_cart_var: ContextVar[list[dict[str, Any]] | None] = ContextVar(
    "tool_current_cart", default=None
)


@contextmanager
def tool_context(session_id: str, current_cart: list[dict[str, Any]] | None) -> Iterator[None]:
    """Set tool context for the current async task."""
    token_session = _session_id_var.set(session_id or "")
    token_cart = _current_cart_var.set(list(current_cart) if current_cart is not None else None)
    try:
        yield
    finally:
        _session_id_var.reset(token_session)
        _current_cart_var.reset(token_cart)


def get_session_id() -> str:
    """Return the current session id from context."""
    return _session_id_var.get()


def get_current_cart() -> list[dict[str, Any]] | None:
    """Return the current cart from context."""
    return _current_cart_var.get()


def sync_local_cart(session_id: str, current_cart: list[dict[str, Any]] | None) -> None:
    """Sync current cart into local in-memory storage."""
    if not session_id or current_cart is None:
        return

    from src.tools.order_tools import _carts

    _carts[session_id] = {
        "items": list(current_cart),
        "last_access": time.time(),
    }
