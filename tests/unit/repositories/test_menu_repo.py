"""Unit tests for MenuRepository query behavior."""

from __future__ import annotations

import unittest
from decimal import Decimal
from types import SimpleNamespace

from src.repositories.menu_repo import MenuRepository


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


class MenuRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = _FakeSession()
        self.repo = MenuRepository(session_factory=_FakeSessionFactory(self.session))

    async def test_search_products_always_filters_selling(self):
        await self.repo.search_products(query="pho")
        stmt_text = str(self.session.last_stmt).lower()
        self.assertTrue(
            "vw_sell_products" in stmt_text or "products.is_selling" in stmt_text,
            msg=f"Unexpected query target: {stmt_text}",
        )

    async def test_get_product_by_id_or_name_returns_record(self):
        self.session.queued_results.append(
            _FakeResult(
                first_row=SimpleNamespace(
                    id=1,
                    name="Phở Bò",
                    description="Món phở bò",
                    price=Decimal("55000"),
                    is_selling=True,
                    category_id=1,
                    category_name="Phở",
                )
            )
        )

        product = await self.repo.get_product_by_id_or_name("phở bò")

        self.assertIsNotNone(product)
        assert product is not None
        self.assertEqual(product.name, "Phở Bò")
        self.assertEqual(int(product.price), 55000)
