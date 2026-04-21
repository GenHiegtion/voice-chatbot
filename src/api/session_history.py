"""In-memory chat history store for multi-turn context in a session."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from threading import Lock

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.config import get_settings

logger = logging.getLogger(__name__)

_MAX_HISTORY_MESSAGES = 30
_histories: dict[str, "_SessionHistory"] = {}
_lock = Lock()


@dataclass(slots=True)
class _SessionHistory:
    messages: list[BaseMessage] = field(default_factory=list)
    last_access: float = field(default_factory=time.time)


def _cleanup_expired_histories(now: float) -> None:
    ttl = max(300, get_settings().cart_ttl_seconds)
    stale_session_ids = [
        session_id
        for session_id, item in _histories.items()
        if now - item.last_access > ttl
    ]
    for session_id in stale_session_ids:
        _histories.pop(session_id, None)

    if stale_session_ids:
        logger.info("SESSION history.cleanup removed=%s", len(stale_session_ids))


def get_session_messages(session_id: str) -> list[BaseMessage]:
    """Return a copy of current session messages for graph input."""
    now = time.time()
    with _lock:
        _cleanup_expired_histories(now)
        session = _histories.get(session_id)
        if not session:
            return []
        session.last_access = now
        return list(session.messages)


def append_session_turn(session_id: str, user_text: str, ai_text: str) -> None:
    """Append one user/assistant turn to session memory."""
    now = time.time()
    with _lock:
        _cleanup_expired_histories(now)
        session = _histories.get(session_id)
        if session is None:
            session = _SessionHistory()
            _histories[session_id] = session

        session.messages.append(HumanMessage(content=user_text))
        session.messages.append(AIMessage(content=ai_text))
        session.messages = session.messages[-_MAX_HISTORY_MESSAGES:]
        session.last_access = now

    logger.info(
        "SESSION history.append session_id=%s total_messages=%s",
        session_id,
        len(session.messages),
    )


def clear_session_history(session_id: str) -> None:
    """Clear one session history (useful for tests)."""
    with _lock:
        _histories.pop(session_id, None)


def clear_all_session_histories() -> None:
    """Clear all session histories (tests only)."""
    with _lock:
        _histories.clear()
