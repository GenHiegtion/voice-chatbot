"""Tool provider selection between local and MCP tools."""

from __future__ import annotations

from src.config import get_settings
from src.tools import menu_tools, promo_tools
from src.tools import mcp_tools as mcp_wrappers
from src.tools.order_tools import add_to_cart, place_order, remove_from_cart, update_cart_quantity, view_cart


def _use_mcp_tools() -> bool:
    return get_settings().tool_provider == "mcp"


def get_menu_tools():
    if _use_mcp_tools():
        return [
            mcp_wrappers.get_menu_categories,
            mcp_wrappers.search_menu,
            mcp_wrappers.get_dish_details,
            mcp_wrappers.get_dishes_by_category,
            mcp_wrappers.get_best_selling_products,
        ]
    return [
        menu_tools.get_menu_categories,
        menu_tools.search_menu,
        menu_tools.get_dish_details,
        menu_tools.get_dishes_by_category,
        menu_tools.get_best_selling_products,
    ]


def get_promotion_tools():
    if _use_mcp_tools():
        return [
            mcp_wrappers.get_active_promotions,
            mcp_wrappers.check_promotion_for_dish,
            mcp_wrappers.get_best_deals,
        ]
    return [
        promo_tools.get_active_promotions,
        promo_tools.check_promotion_for_dish,
        promo_tools.get_best_deals,
    ]


def get_order_tools():
    if _use_mcp_tools():
        return [
            mcp_wrappers.add_to_cart,
            mcp_wrappers.remove_from_cart,
            mcp_wrappers.view_cart,
            mcp_wrappers.update_cart_quantity,
            mcp_wrappers.place_order,
        ]
    return [add_to_cart, remove_from_cart, view_cart, update_cart_quantity, place_order]
