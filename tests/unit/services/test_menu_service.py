"""Unit tests for MenuService."""

from __future__ import annotations

import unittest
from decimal import Decimal

from src.repositories.records import CategoryRecord, ProductRecord, PromotionRecord
from src.services.menu_service import MenuService


class _FakeMenuRepo:
    def __init__(self):
        self.last_search_kwargs = None

    async def list_categories(self):
        return [CategoryRecord(id=1, name="Phở"), CategoryRecord(id=2, name="Cơm")]

    async def search_products(self, **kwargs):
        self.last_search_kwargs = kwargs
        return [
            ProductRecord(
                id=1,
                name="Phở Bò",
                description="Phở truyền thống",
                price=Decimal("55000"),
                is_selling=True,
                category_id=1,
                category_name="Phở",
            )
        ]

    async def get_product_by_id_or_name(self, _dish):
        return ProductRecord(
            id=1,
            name="Phở Bò",
            description="Phở truyền thống",
            price=Decimal("55000"),
            is_selling=True,
            category_id=1,
            category_name="Phở",
        )

    async def get_products_by_category(self, _category):
        return [
            ProductRecord(
                id=2,
                name="Phở Gà",
                description="Phở gà ta",
                price=Decimal("50000"),
                is_selling=True,
                category_id=1,
                category_name="Phở",
            )
        ]


class _FakePromoRepo:
    async def get_promotion_for_product(self, _product_id):
        return PromotionRecord(
            id=10,
            product_id=1,
            product_name="Phở Bò",
            product_price=Decimal("55000"),
            discount=Decimal("20"),
            start_date=None,
            end_date=None,
            is_active=True,
        )


class MenuServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.menu_repo = _FakeMenuRepo()
        self.service = MenuService(menu_repo=self.menu_repo, promo_repo=_FakePromoRepo())

    async def test_get_menu_categories(self):
        text = await self.service.get_menu_categories()
        self.assertIn("Danh mục hiện có", text)
        self.assertIn("Phở", text)

    async def test_search_menu_extracts_price_bound(self):
        await self.service.search_menu("món phở dưới 60k")
        self.assertEqual(self.menu_repo.last_search_kwargs["max_price"], 60000)

    async def test_get_dish_details_contains_discount(self):
        text = await self.service.get_dish_details("Phở Bò")
        self.assertIn("Giá sau ưu đãi", text)
