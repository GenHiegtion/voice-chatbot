"""Base repository utilities for read-only access."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database import get_session_factory


class ReadOnlyRepository:
    """Read-only repository base class.

    The repository provides only query methods and always rolls back
    before closing a session to avoid accidental writes.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None):
        self._session_factory = session_factory

    def _resolve_session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self._session_factory = get_session_factory()
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        factory = self._resolve_session_factory()
        async with factory() as session:
            try:
                yield session
            finally:
                # Keep the read-only contract explicit even if future code changes.
                await session.rollback()
