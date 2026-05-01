"""LangChain tool wrappers that call MCP server."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from src.mcp.client import call_mcp_tool
from src.tools import order_tools
from src.tools.tool_context import get_current_cart, get_session_id, sync_local_cart


def _context_payload(session_id: str | None = None) -> tuple[str, dict[str, Any]]:
    actual_session_id = (session_id or get_session_id()).strip()
    payload: dict[str, Any] = {"session_id": actual_session_id}
    current_cart = get_current_cart()
    if current_cart is not None:
        payload["current_cart"] = current_cart
    return actual_session_id, payload


@tool
async def get_menu_categories() -> str:
    """Fetch menu categories via MCP."""
    session_id, payload = _context_payload()
    if not session_id:
        return "Missing session_id for MCP call."
    return await call_mcp_tool("menu_get_menu_categories", payload)


@tool
async def search_menu(
    query: str,
    category: str = "",
    min_price: int = 0,
    max_price: int = 0,
) -> str:
    """Search menu via MCP."""
    session_id, payload = _context_payload()
    if not session_id:
        return "Missing session_id for MCP call."
    payload.update(
        {
            "query": query,
            "category": category,
            "min_price": min_price,
            "max_price": max_price,
        }
    )
    return await call_mcp_tool("menu_search_menu", payload)


@tool
async def get_dish_details(dish_name_or_id: str) -> str:
    """Get dish details via MCP."""
    session_id, payload = _context_payload()
    if not session_id:
        return "Missing session_id for MCP call."
    payload["dish_name_or_id"] = dish_name_or_id
    return await call_mcp_tool("menu_get_dish_details", payload)


@tool
async def get_dishes_by_category(category: str) -> str:
    """Get dishes by category via MCP."""
    session_id, payload = _context_payload()
    if not session_id:
        return "Missing session_id for MCP call."
    payload["category"] = category
    return await call_mcp_tool("menu_get_dishes_by_category", payload)


@tool
async def get_best_selling_products(limit: int = 5) -> str:
    """Get best selling products via MCP."""
    session_id, payload = _context_payload()
    if not session_id:
        return "Missing session_id for MCP call."
    payload["limit"] = limit
    return await call_mcp_tool("menu_get_best_selling_products", payload)


@tool
async def get_active_promotions() -> str:
    """Fetch promotions via MCP."""
    session_id, payload = _context_payload()
    if not session_id:
        return "Missing session_id for MCP call."
    return await call_mcp_tool("promotion_get_active_promotions", payload)


@tool
async def check_promotion_for_dish(dish_name_or_id: str) -> str:
    """Check promotion for dish via MCP."""
    session_id, payload = _context_payload()
    if not session_id:
        return "Missing session_id for MCP call."
    payload["dish_name_or_id"] = dish_name_or_id
    return await call_mcp_tool("promotion_check_promotion_for_dish", payload)


@tool
async def get_best_deals(limit: int = 5) -> str:
    """Get best deals via MCP."""
    session_id, payload = _context_payload()
    if not session_id:
        return "Missing session_id for MCP call."
    payload["limit"] = limit
    return await call_mcp_tool("promotion_get_best_deals", payload)


@tool
async def add_to_cart(session_id: str, dish_name: str, quantity: int = 1) -> str:
    """Add to cart via MCP."""
    actual_session_id, payload = _context_payload(session_id)
    if not actual_session_id:
        return "Missing session_id for MCP call."
    payload.update({"dish_name": dish_name, "quantity": quantity})
    response = await call_mcp_tool("order_add_to_cart", payload)
    sync_local_cart(actual_session_id, payload.get("current_cart"))
    try:
        order_tools.add_to_cart.func(
            session_id=actual_session_id,
            dish_name=dish_name,
            quantity=quantity,
        )
    except Exception:
        pass
    return response


@tool
async def remove_from_cart(session_id: str, dish_name: str) -> str:
    """Remove from cart via MCP."""
    actual_session_id, payload = _context_payload(session_id)
    if not actual_session_id:
        return "Missing session_id for MCP call."
    payload["dish_name"] = dish_name
    response = await call_mcp_tool("order_remove_from_cart", payload)
    sync_local_cart(actual_session_id, payload.get("current_cart"))
    try:
        order_tools.remove_from_cart.func(session_id=actual_session_id, dish_name=dish_name)
    except Exception:
        pass
    return response


@tool
async def view_cart(session_id: str) -> str:
    """View cart via MCP."""
    actual_session_id, payload = _context_payload(session_id)
    if not actual_session_id:
        return "Missing session_id for MCP call."
    response = await call_mcp_tool("order_view_cart", payload)
    sync_local_cart(actual_session_id, payload.get("current_cart"))
    try:
        order_tools.view_cart.func(session_id=actual_session_id)
    except Exception:
        pass
    return response


@tool
async def update_cart_quantity(session_id: str, dish_name: str, quantity: int) -> str:
    """Update cart quantity via MCP."""
    actual_session_id, payload = _context_payload(session_id)
    if not actual_session_id:
        return "Missing session_id for MCP call."
    payload.update({"dish_name": dish_name, "quantity": quantity})
    response = await call_mcp_tool("order_update_cart_quantity", payload)
    sync_local_cart(actual_session_id, payload.get("current_cart"))
    try:
        order_tools.update_cart_quantity.func(
            session_id=actual_session_id,
            dish_name=dish_name,
            quantity=quantity,
        )
    except Exception:
        pass
    return response


@tool
async def place_order(session_id: str, delivery_address: str = "", note: str = "") -> str:
    """Place order via MCP."""
    actual_session_id, payload = _context_payload(session_id)
    if not actual_session_id:
        return "Missing session_id for MCP call."
    payload.update({"delivery_address": delivery_address, "note": note})
    response = await call_mcp_tool("order_place_order", payload)
    sync_local_cart(actual_session_id, payload.get("current_cart"))
    try:
        order_tools.place_order.func(
            session_id=actual_session_id,
            delivery_address=delivery_address,
            note=note,
        )
    except Exception:
        pass
    return response
