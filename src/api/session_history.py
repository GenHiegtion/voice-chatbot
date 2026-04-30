"""Session history store with optional Redis backend."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Iterable

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from redis.exceptions import RedisError

from src.config import get_settings
from src.redis_client import get_redis_client

logger = logging.getLogger(__name__)

_MAX_HISTORY_MESSAGES = 30
_HISTORY_KEY_PREFIX = "history:"
_histories: dict[str, "_SessionHistory"] = {}
_lock = Lock()


@dataclass(slots=True)
class _SessionHistory:
    messages: list[BaseMessage] = field(default_factory=list)
    last_access: float = field(default_factory=time.time)


def _cleanup_expired_histories(now: float) -> None:
    ttl = max(300, get_settings().redis_ttl_seconds)
    stale_session_ids = [
        session_id
        for session_id, item in _histories.items()
        if now - item.last_access > ttl
    ]
    for session_id in stale_session_ids:
        _histories.pop(session_id, None)

    if stale_session_ids:
        logger.info("SESSION history.cleanup removed=%s", len(stale_session_ids))


def _history_key(session_id: str) -> str:
    return f"{_HISTORY_KEY_PREFIX}{session_id}"


def _redis_ttl_seconds() -> int:
    return max(60, get_settings().redis_ttl_seconds)


def _messages_to_payload(messages: Iterable[BaseMessage]) -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []
    for msg in messages:
        role = getattr(msg, "type", "human")
        payload.append({"role": role, "content": msg.content})
    return payload


def _payload_to_messages(payload: list[dict]) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        role = item.get("role", "human")
        content = item.get("content", "")
        if role == "ai":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    return messages


def _load_history_from_redis(session_id: str) -> list[BaseMessage] | None:
    client = get_redis_client()
    if client is None:
        return None

    key = _history_key(session_id)
    try:
        raw = client.get(key)
    except RedisError:
        logger.warning(
            "SESSION history.redis_get_failed session_id=%s",
            session_id,
            exc_info=True,
        )
        return None

    if not raw:
        return []

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(
            "SESSION history.redis_decode_failed session_id=%s",
            session_id,
            exc_info=True,
        )
        return []

    if not isinstance(payload, list):
        logger.warning("SESSION history.redis_payload_invalid session_id=%s", session_id)
        return []

    messages = _payload_to_messages(payload)
    return messages[-_MAX_HISTORY_MESSAGES:]


def _save_history_to_redis(session_id: str, messages: list[BaseMessage]) -> bool:
    client = get_redis_client()
    if client is None:
        return False

    key = _history_key(session_id)
    payload = _messages_to_payload(messages[-_MAX_HISTORY_MESSAGES:])
    try:
        client.set(key, json.dumps(payload), ex=_redis_ttl_seconds())
    except RedisError:
        logger.warning(
            "SESSION history.redis_set_failed session_id=%s",
            session_id,
            exc_info=True,
        )
        return False

    return True


def get_session_messages(session_id: str) -> list[BaseMessage]:
    """Return a copy of current session messages for graph input."""
    redis_messages = _load_history_from_redis(session_id)
    if redis_messages is not None:
        logger.info(
            "SESSION history.redis_loaded session_id=%s messages=%s",
            session_id,
            len(redis_messages),
        )
        return redis_messages

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
    redis_messages = _load_history_from_redis(session_id)
    if redis_messages is not None:
        redis_messages.append(HumanMessage(content=user_text))
        redis_messages.append(AIMessage(content=ai_text))
        redis_messages = redis_messages[-_MAX_HISTORY_MESSAGES:]
        if _save_history_to_redis(session_id, redis_messages):
            logger.info(
                "SESSION history.redis_append session_id=%s total_messages=%s",
                session_id,
                len(redis_messages),
            )
            return

        logger.warning("SESSION history.redis_fallback session_id=%s", session_id)

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
    client = get_redis_client()
    if client is not None:
        try:
            client.delete(_history_key(session_id))
        except RedisError:
            logger.warning(
                "SESSION history.redis_delete_failed session_id=%s",
                session_id,
                exc_info=True,
            )
    with _lock:
        _histories.pop(session_id, None)


def clear_all_session_histories() -> None:
    """Clear all session histories (tests only)."""
    client = get_redis_client()
    if client is not None:
        try:
            client.flushdb()
        except RedisError:
            logger.warning("SESSION history.redis_flush_failed", exc_info=True)
    with _lock:
        _histories.clear()
