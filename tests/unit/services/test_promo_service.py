"""Unit tests for PromotionService."""

from __future__ import annotations

import unittest
from decimal import Decimal

from src.repositories.records import ProductRecord, PromotionRecord
from src.services.promo_service import PromotionService


class _FakePromoRepo:
    async def list_active_promotions(self):
        return [
            PromotionRecord(
                id=1,
                product_id=2,
                product_name="Cơm Gà",
                product_price=Decimal("55000"),
                discount=Decimal("15"),
                start_date=None,
                end_date=None,
                is_active=True,
            )
        ]

    async def get_promotion_for_product(self, product_id):
        if product_id == 999:
            return None
        return PromotionRecord(
            id=2,
            product_id=product_id,
            product_name="Phở Bò",
            product_price=Decimal("55000"),
            discount=Decimal("20"),
            start_date=None,
            end_date=None,
            is_active=True,
        )

    async def get_best_deals(self, limit=5):
        deals = await self.list_active_promotions()
        return deals[:limit]


class _FakeMenuRepo:
    async def get_product_by_id_or_name(self, dish):
        if dish == "khong-ton-tai":
            return None
        if dish == "khong-uu-dai":
            return ProductRecord(
                id=999,
                name="Món Không Ưu Đãi",
                description="",
                price=Decimal("45000"),
                is_selling=True,
                category_id=1,
                category_name="Phở",
            )
        return ProductRecord(
            id=1,
            name="Phở Bò",
            description="",
            price=Decimal("55000"),
            is_selling=True,
            category_id=1,
            category_name="Phở",
        )


class PromotionServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.service = PromotionService(promo_repo=_FakePromoRepo(), menu_repo=_FakeMenuRepo())

    async def test_get_active_promotions(self):
        text = await self.service.get_active_promotions()
        self.assertIn("Ưu đãi", text)
        self.assertIn("Cơm Gà", text)

    async def test_check_promotion_for_dish_not_found(self):
        text = await self.service.check_promotion_for_dish("khong-ton-tai")
        self.assertIn("Không tìm thấy", text)

    async def test_check_promotion_for_dish_without_promo(self):
        text = await self.service.check_promotion_for_dish("khong-uu-dai")
        self.assertIn("chưa có ưu đãi", text)
