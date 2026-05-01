"""Helpers for MCP tool context synchronization."""

from __future__ import annotations

import time
from typing import Any

from langchain_core.messages import BaseMessage

from src.api.session_history import get_session_messages
from src.tools.order_tools import _carts


def sync_current_cart(session_id: str, current_cart: list[dict[str, Any]] | None) -> None:
    """Sync app cart into the in-memory cart store for this session."""
    if not session_id or current_cart is None:
        return

    _carts[session_id] = {
        "items": list(current_cart),
        "last_access": time.time(),
    }


def load_session_history(session_id: str) -> list[BaseMessage]:
    """Load recent session history from the configured backend."""
    if not session_id:
        return []
    return get_session_messages(session_id)
