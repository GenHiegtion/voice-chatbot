"""Database configuration for MySQL connection.

This module provides async MySQL engine/session utilities
for repository and service layers.

# Setup guide:
# 1. Add database credentials to your .env file:
#    DB_HOST=localhost
#    DB_PORT=3306
#    DB_USER=your_user
#    DB_PASSWORD=your_password
#    DB_NAME=food_ordering
#
# 2. Example usage in repositories/services:
#    from src.database import get_db_session
#    from sqlalchemy import text
#
#    async def get_menu_from_db():
#        async with get_db_session() as session:
#            result = await session.execute(text("SELECT * FROM menu_items"))
#            return result.fetchall()
"""

import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import get_settings

logger = logging.getLogger(__name__)

# Singleton engine
_engine = None
_session_factory = None


def get_engine():
    """Create or get the async database engine."""
    global _engine

    if _engine is not None:
        return _engine

    settings = get_settings()

    if not settings.db_host:
        raise RuntimeError(
            "Database is not configured. "
            "Please set DB_HOST, DB_USER, DB_PASSWORD, DB_NAME in your .env file."
        )

    # Build MySQL connection URL for aiomysql
    db_url = (
        f"mysql+aiomysql://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )

    _engine = create_async_engine(
        db_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,
    )

    logger.info(
        "Database engine initialized host=%s port=%s db=%s",
        settings.db_host,
        settings.db_port,
        settings.db_name,
    )
    return _engine


def get_session_factory():
    """Get the async session factory."""
    global _session_factory

    if _session_factory is not None:
        return _session_factory

    engine = get_engine()
    _session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False)
    return _session_factory


async def close_engine() -> None:
    """Dispose global database engine and reset factories.

    Safe to call multiple times.
    """
    global _engine, _session_factory

    if _engine is None:
        return

    await _engine.dispose()
    _engine = None
    _session_factory = None
    logger.info("Database engine disposed")


async def probe_database_connection() -> bool:
    """Run a lightweight read-only DB probe (SELECT 1)."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connectivity check succeeded")
        return True
    except Exception:
        logger.exception("Database connectivity check failed")
        return False


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions.

    Usage:
        async with get_db_session() as session:
            result = await session.execute(...)
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
