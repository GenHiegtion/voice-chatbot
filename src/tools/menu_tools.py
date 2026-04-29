"""Database-backed menu tools for the menu agent."""

from __future__ import annotations

import logging

from langchain_core.tools import tool

from src.services.menu_service import MenuService

logger = logging.getLogger(__name__)
_service = MenuService()


def _optional_price(value: int) -> int | None:
    return value if value and value > 0 else None


@tool
async def get_menu_categories() -> str:
    """Fetch menu categories from the database."""
    logger.info("TOOL menu_tools.get_menu_categories.start")
    try:
        result = await _service.get_menu_categories()
        logger.info("TOOL menu_tools.get_menu_categories.success chars=%s", len(result))
        return result
    except RuntimeError as exc:
        logger.warning("TOOL menu_tools.get_menu_categories.db_unavailable error=%s", exc)
        return "Hiện chưa cấu hình kết nối cơ sở dữ liệu cho thực đơn."
    except Exception:
        logger.exception("TOOL menu_tools.get_menu_categories.failed")
        return "Không thể tải danh mục món ăn lúc này. Vui lòng thử lại sau."


@tool
async def search_menu(query: str, category: str = "", min_price: int = 0, max_price: int = 0) -> str:
    """Search dishes by keyword, category, and price range.

    Args:
        query: Search keyword for dishes
        category: Dish category (optional)
        min_price: Minimum price in VND (optional)
        max_price: Maximum price in VND (optional)
    """
    logger.info(
        "TOOL menu_tools.search_menu.start query=%s category=%s min_price=%s max_price=%s",
        query,
        category,
        min_price,
        max_price,
    )
    try:
        result = await _service.search_menu(
            query=query,
            category=category or None,
            min_price=_optional_price(min_price),
            max_price=_optional_price(max_price),
        )
        logger.info("TOOL menu_tools.search_menu.success chars=%s", len(result))
        return result
    except RuntimeError as exc:
        logger.warning("TOOL menu_tools.search_menu.db_unavailable error=%s", exc)
        return "Hiện chưa cấu hình kết nối cơ sở dữ liệu để tìm món."
    except Exception:
        logger.exception("TOOL menu_tools.search_menu.failed")
        return "Không thể tìm món lúc này. Bạn vui lòng thử lại sau."


@tool
async def get_dish_details(dish_name_or_id: str) -> str:
    """Get dish details by name or ID."""
    logger.info("TOOL menu_tools.get_dish_details.start ref=%s", dish_name_or_id)
    try:
        result = await _service.get_dish_details(dish_name_or_id)
        logger.info("TOOL menu_tools.get_dish_details.success chars=%s", len(result))
        return result
    except RuntimeError as exc:
        logger.warning("TOOL menu_tools.get_dish_details.db_unavailable error=%s", exc)
        return "Hiện chưa cấu hình kết nối cơ sở dữ liệu để lấy chi tiết món."
    except Exception:
        logger.exception("TOOL menu_tools.get_dish_details.failed")
        return "Không thể lấy chi tiết món lúc này. Bạn vui lòng thử lại sau."


@tool
async def get_dishes_by_category(category: str) -> str:
    """Get currently selling dishes by category."""
    logger.info("TOOL menu_tools.get_dishes_by_category.start category=%s", category)
    try:
        result = await _service.get_dishes_by_category(category)
        logger.info("TOOL menu_tools.get_dishes_by_category.success chars=%s", len(result))
        return result
    except RuntimeError as exc:
        logger.warning("TOOL menu_tools.get_dishes_by_category.db_unavailable error=%s", exc)
        return "Hiện chưa cấu hình kết nối cơ sở dữ liệu để lọc món theo danh mục."
    except Exception:
        logger.exception("TOOL menu_tools.get_dishes_by_category.failed")
        return "Không thể lọc món theo danh mục lúc này. Bạn vui lòng thử lại sau."


@tool
def transfer_to_order_agent() -> str:
    """Use this tool to HAND OFF to order_agent.
    Call this tool immediately after you have verified the dish exists
    and the user wants to add it to the cart.
    """
    logger.info("TOOL menu_tools.transfer_to_order_agent.called")
    return "TRANSFER_SIGNAL_SENT"

@tool
async def get_best_selling_products(limit: int = 5) -> str:
    """Get the list of best-selling dishes.
    
    Args:
        limit: Number of items to return (default 5, max 20)
    """
    logger.info("TOOL menu_tools.get_best_selling_products.start limit=%s", limit)
    try:
        result = await _service.get_best_selling_products(limit)
        logger.info("TOOL menu_tools.get_best_selling_products.success chars=%s", len(result))
        return result
    except RuntimeError as exc:
        logger.warning("TOOL menu_tools.get_best_selling_products.db_unavailable error=%s", exc)
        return "Hiện chưa cấu hình kết nối cơ sở dữ liệu để lấy danh sách món bán chạy."
    except Exception:
        logger.exception("TOOL menu_tools.get_best_selling_products.failed")
        return "Không thể lấy danh sách món bán chạy lúc này. Bạn vui lòng thử lại sau."
