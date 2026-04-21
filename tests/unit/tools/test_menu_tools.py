"""Unit tests for menu_tools."""

from __future__ import annotations

import unittest

from src.tools import menu_tools


class _FakeMenuService:
    async def get_menu_categories(self):
        return "Danh mục test"

    async def search_menu(self, **_kwargs):
        return "Kết quả search test"

    async def get_dish_details(self, _dish_name_or_id):
        return "Chi tiết món test"

    async def get_dishes_by_category(self, _category):
        return "Danh sách theo danh mục test"


class MenuToolsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_service = menu_tools._service
        menu_tools._service = _FakeMenuService()

    async def asyncTearDown(self):
        menu_tools._service = self.original_service

    async def test_get_menu_categories_tool(self):
        output = await menu_tools.get_menu_categories.ainvoke({})
        self.assertEqual(output, "Danh mục test")

    async def test_search_menu_tool(self):
        output = await menu_tools.search_menu.ainvoke({"query": "phở", "max_price": 60000})
        self.assertEqual(output, "Kết quả search test")

    async def test_get_dish_details_tool(self):
        output = await menu_tools.get_dish_details.ainvoke({"dish_name_or_id": "phở bò"})
        self.assertEqual(output, "Chi tiết món test")
