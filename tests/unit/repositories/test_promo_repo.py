"""Unit tests for PromotionRepository query behavior."""

from __future__ import annotations

import unittest

from src.repositories.promo_repo import PromotionRepository


class _FakeResult:
    def __init__(self, rows=None, first_row=None):
        self._rows = rows or []
        self._first_row = first_row

    def all(self):
        return self._rows

    def first(self):
        return self._first_row


class _FakeSession:
    def __init__(self):
        self.queued_results = []
        self.last_stmt = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, stmt, params=None):
        del params
        self.last_stmt = stmt
        if self.queued_results:
            return self.queued_results.pop(0)
        return _FakeResult()

    async def rollback(self):
        return None


class _FakeSessionFactory:
    def __init__(self, session):
        self.session = session

    def __call__(self):
        return self.session


class PromotionRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = _FakeSession()
        self.repo = PromotionRepository(session_factory=_FakeSessionFactory(self.session))

    async def test_list_active_promotions_uses_active_filters(self):
        await self.repo.list_active_promotions()

        stmt_text = str(self.session.last_stmt).lower()
        self.assertTrue(
            "vw_product_active_deals" in stmt_text
            or ("sale_offs.is_active" in stmt_text and "products.is_selling" in stmt_text),
            msg=f"Unexpected query target: {stmt_text}",
        )

    async def test_get_best_deals_limits_result_size(self):
        deals = await self.repo.get_best_deals(limit=50)
        self.assertLessEqual(len(deals), 20)
