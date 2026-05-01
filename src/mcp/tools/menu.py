"""MCP adapters for menu tools."""

from __future__ import annotations

from typing import Any

from src.mcp.context import sync_current_cart
from src.tools import menu_tools


async def menu_get_menu_categories(
    session_id: str,
    current_cart: list[dict[str, Any]] | None = None,
) -> str:
    """Return menu categories."""
    sync_current_cart(session_id, current_cart)
    return await menu_tools.get_menu_categories.coroutine()


async def menu_search_menu(
    session_id: str,
    query: str,
    category: str = "",
    min_price: int = 0,
    max_price: int = 0,
    current_cart: list[dict[str, Any]] | None = None,
) -> str:
    """Search dishes by keyword and filters."""
    sync_current_cart(session_id, current_cart)
    return await menu_tools.search_menu.coroutine(
        query=query,
        category=category,
        min_price=min_price,
        max_price=max_price,
    )


async def menu_get_dish_details(
    session_id: str,
    dish_name_or_id: str,
    current_cart: list[dict[str, Any]] | None = None,
) -> str:
    """Get dish details by name or ID."""
    sync_current_cart(session_id, current_cart)
    return await menu_tools.get_dish_details.coroutine(dish_name_or_id=dish_name_or_id)


async def menu_get_dishes_by_category(
    session_id: str,
    category: str,
    current_cart: list[dict[str, Any]] | None = None,
) -> str:
    """Get dishes by category."""
    sync_current_cart(session_id, current_cart)
    return await menu_tools.get_dishes_by_category.coroutine(category=category)


async def menu_get_best_selling_products(
    session_id: str,
    limit: int = 5,
    current_cart: list[dict[str, Any]] | None = None,
) -> str:
    """Get best-selling dishes."""
    sync_current_cart(session_id, current_cart)
    return await menu_tools.get_best_selling_products.coroutine(limit=limit)
