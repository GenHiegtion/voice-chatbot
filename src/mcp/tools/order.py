"""MCP adapters for order tools."""

from __future__ import annotations

from typing import Any

from src.mcp.context import sync_current_cart
from src.tools import order_tools


def order_add_to_cart(
    session_id: str,
    dish_name: str,
    quantity: int = 1,
    current_cart: list[dict[str, Any]] | None = None,
) -> str:
    """Add a dish to the cart."""
    sync_current_cart(session_id, current_cart)
    return order_tools.add_to_cart.func(
        session_id=session_id,
        dish_name=dish_name,
        quantity=quantity,
    )


def order_remove_from_cart(
    session_id: str,
    dish_name: str,
    current_cart: list[dict[str, Any]] | None = None,
) -> str:
    """Remove a dish from the cart."""
    sync_current_cart(session_id, current_cart)
    return order_tools.remove_from_cart.func(session_id=session_id, dish_name=dish_name)


def order_view_cart(
    session_id: str,
    current_cart: list[dict[str, Any]] | None = None,
) -> str:
    """View cart contents."""
    sync_current_cart(session_id, current_cart)
    return order_tools.view_cart.func(session_id=session_id)


def order_update_cart_quantity(
    session_id: str,
    dish_name: str,
    quantity: int,
    current_cart: list[dict[str, Any]] | None = None,
) -> str:
    """Update quantity for a dish in the cart."""
    sync_current_cart(session_id, current_cart)
    return order_tools.update_cart_quantity.func(
        session_id=session_id,
        dish_name=dish_name,
        quantity=quantity,
    )


def order_place_order(
    session_id: str,
    delivery_address: str = "",
    note: str = "",
    current_cart: list[dict[str, Any]] | None = None,
) -> str:
    """Place an order with the current cart."""
    sync_current_cart(session_id, current_cart)
    return order_tools.place_order.func(
        session_id=session_id,
        delivery_address=delivery_address,
        note=note,
    )
