"""Redis client helper for optional session history storage."""

from __future__ import annotations

import logging

from redis import Redis
from redis.exceptions import RedisError

from src.config import get_settings

logger = logging.getLogger(__name__)

_client: Redis | None = None
_client_ready = False


def get_redis_client() -> Redis | None:
    """Return a ready Redis client or None when disabled/unavailable."""
    settings = get_settings()
    if not settings.redis_enabled:
        return None
    if not settings.redis_url:
        logger.warning("REDIS disabled_missing_url")
        return None

    global _client, _client_ready
    if _client is None:
        _client = Redis.from_url(settings.redis_url, decode_responses=True)
        _client_ready = False

    if not _client_ready:
        try:
            _client.ping()
            _client_ready = True
            logger.info("REDIS client_ready")
        except RedisError:
            logger.warning("REDIS ping_failed", exc_info=True)
            return None

    return _client
