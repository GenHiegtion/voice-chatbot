"""Unit tests for MCP context helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from langchain_core.messages import HumanMessage

from src.mcp.context import load_session_history, sync_current_cart
from src.tools.order_tools import _carts


class McpContextTest(unittest.TestCase):
    def tearDown(self) -> None:
        _carts.clear()

    def test_sync_current_cart_updates_store(self) -> None:
        cart = [{"id": "1", "name": "Pho", "quantity": 1}]
        sync_current_cart("s-1", cart)

        self.assertIn("s-1", _carts)
        self.assertEqual(_carts["s-1"]["items"], cart)

    def test_load_session_history_uses_backend(self) -> None:
        with patch(
            "src.mcp.context.get_session_messages",
            return_value=[HumanMessage(content="hello")],
        ) as mock_get:
            messages = load_session_history("s-2")

        self.assertEqual(len(messages), 1)
        mock_get.assert_called_once_with("s-2")
