"""MCP adapters for promotion tools."""

from __future__ import annotations

from typing import Any

from src.mcp.context import sync_current_cart
from src.tools import promo_tools


async def promotion_get_active_promotions(
    session_id: str,
    current_cart: list[dict[str, Any]] | None = None,
) -> str:
    """List active promotions."""
    sync_current_cart(session_id, current_cart)
    return await promo_tools.get_active_promotions.coroutine()


async def promotion_check_promotion_for_dish(
    session_id: str,
    dish_name_or_id: str,
    current_cart: list[dict[str, Any]] | None = None,
) -> str:
    """Check promotion for a specific dish."""
    sync_current_cart(session_id, current_cart)
    return await promo_tools.check_promotion_for_dish.coroutine(dish_name_or_id=dish_name_or_id)


async def promotion_get_best_deals(
    session_id: str,
    limit: int = 5,
    current_cart: list[dict[str, Any]] | None = None,
) -> str:
    """Get top promotion deals."""
    sync_current_cart(session_id, current_cart)
    return await promo_tools.get_best_deals.coroutine(limit=limit)
