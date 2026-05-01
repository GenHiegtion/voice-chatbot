"""Unit tests for MCP tool adapters."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from src.mcp.tools import menu as menu_mcp
from src.mcp.tools import order as order_mcp
from src.mcp.tools import promotion as promo_mcp
from src.tools import menu_tools, order_tools, promo_tools
from src.tools.order_tools import _carts


class McpMenuToolsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        _carts.clear()

    async def test_menu_get_menu_categories(self) -> None:
        with patch.object(
            menu_tools.get_menu_categories,
            "coroutine",
            new=AsyncMock(return_value="menu-ok"),
        ) as mock_call:
            result = await menu_mcp.menu_get_menu_categories(
                "s-1", current_cart=[{"id": "1"}]
            )

        self.assertEqual(result, "menu-ok")
        mock_call.assert_awaited_once_with()
        self.assertIn("s-1", _carts)


class McpPromotionToolsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        _carts.clear()

    async def test_promotion_get_best_deals(self) -> None:
        with patch.object(
            promo_tools.get_best_deals,
            "coroutine",
            new=AsyncMock(return_value="promo-ok"),
        ) as mock_call:
            result = await promo_mcp.promotion_get_best_deals(
                "s-2", limit=3, current_cart=[{"id": "2"}]
            )

        self.assertEqual(result, "promo-ok")
        mock_call.assert_awaited_once_with(limit=3)
        self.assertIn("s-2", _carts)


class McpOrderToolsTest(unittest.TestCase):
    def tearDown(self) -> None:
        _carts.clear()

    def test_order_add_to_cart(self) -> None:
        with patch.object(
            order_tools.add_to_cart,
            "func",
            return_value="order-ok",
        ) as mock_call:
            result = order_mcp.order_add_to_cart(
                "s-3", "Pho", quantity=2, current_cart=[{"id": "3"}]
            )

        self.assertEqual(result, "order-ok")
        mock_call.assert_called_once_with(session_id="s-3", dish_name="Pho", quantity=2)
        self.assertIn("s-3", _carts)
