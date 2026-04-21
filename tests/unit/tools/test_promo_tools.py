"""Unit tests for promo_tools."""

from __future__ import annotations

import unittest

from src.tools import promo_tools


class _FakePromoService:
    async def get_active_promotions(self):
        return "Ưu đãi test"

    async def check_promotion_for_dish(self, _dish_name_or_id):
        return "Ưu đãi theo món test"

    async def get_best_deals(self, limit=5):
        return f"Top {limit} test"


class PromoToolsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_service = promo_tools._service
        promo_tools._service = _FakePromoService()

    async def asyncTearDown(self):
        promo_tools._service = self.original_service

    async def test_get_active_promotions_tool(self):
        output = await promo_tools.get_active_promotions.ainvoke({})
        self.assertEqual(output, "Ưu đãi test")

    async def test_check_promotion_for_dish_tool(self):
        output = await promo_tools.check_promotion_for_dish.ainvoke({"dish_name_or_id": "phở bò"})
        self.assertEqual(output, "Ưu đãi theo món test")

    async def test_get_best_deals_tool(self):
        output = await promo_tools.get_best_deals.ainvoke({"limit": 3})
        self.assertEqual(output, "Top 3 test")
