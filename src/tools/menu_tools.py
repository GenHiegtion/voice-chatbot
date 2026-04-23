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
    """Lấy danh sách danh mục món ăn từ cơ sở dữ liệu."""
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
    """Tìm món theo từ khóa, danh mục và khoảng giá.

    Args:
        query: Từ khóa tìm kiếm món ăn
        category: Danh mục món (không bắt buộc)
        min_price: Giá tối thiểu VND (không bắt buộc)
        max_price: Giá tối đa VND (không bắt buộc)
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
    """Lấy thông tin chi tiết món ăn theo tên hoặc ID."""
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
    """Lấy danh sách món đang bán theo danh mục."""
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
    """Sử dụng công cụ này ĐỂ CHUYỂN GIAO (HANDOFF) sang order_agent.
    Gọi công cụ này NGAY LẬP TỨC sau khi bạn đã xác minh món ăn tồn tại
    và người dùng muốn thêm món đó vào giỏ hàng.
    """
    logger.info("TOOL menu_tools.transfer_to_order_agent.called")
    return "TRANSFER_SIGNAL_SENT"
