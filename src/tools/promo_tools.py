"""Database-backed promotion tools for the promotion agent."""

from __future__ import annotations

import logging

from langchain_core.tools import tool

from src.services.promo_service import PromotionService

logger = logging.getLogger(__name__)
_service = PromotionService()


@tool
async def get_active_promotions() -> str:
    """Lấy danh sách ưu đãi đang còn hiệu lực."""
    logger.info("TOOL promo_tools.get_active_promotions.start")
    try:
        result = await _service.get_active_promotions()
        logger.info("TOOL promo_tools.get_active_promotions.success chars=%s", len(result))
        return result
    except RuntimeError as exc:
        logger.warning("TOOL promo_tools.get_active_promotions.db_unavailable error=%s", exc)
        return "Hiện chưa cấu hình kết nối cơ sở dữ liệu ưu đãi."
    except Exception:
        logger.exception("TOOL promo_tools.get_active_promotions.failed")
        return "Không thể tải danh sách ưu đãi lúc này."


@tool
async def check_promotion_for_dish(dish_name_or_id: str) -> str:
    """Kiểm tra ưu đãi đang áp dụng cho một món cụ thể."""
    logger.info("TOOL promo_tools.check_promotion_for_dish.start ref=%s", dish_name_or_id)
    try:
        result = await _service.check_promotion_for_dish(dish_name_or_id)
        logger.info("TOOL promo_tools.check_promotion_for_dish.success chars=%s", len(result))
        return result
    except RuntimeError as exc:
        logger.warning("TOOL promo_tools.check_promotion_for_dish.db_unavailable error=%s", exc)
        return "Hiện chưa cấu hình kết nối cơ sở dữ liệu ưu đãi theo món."
    except Exception:
        logger.exception("TOOL promo_tools.check_promotion_for_dish.failed")
        return "Không thể kiểm tra ưu đãi cho món này lúc này."


@tool
async def get_best_deals(limit: int = 5) -> str:
    """Lấy danh sách món có mức ưu đãi tốt nhất."""
    logger.info("TOOL promo_tools.get_best_deals.start limit=%s", limit)
    try:
        result = await _service.get_best_deals(limit=limit)
        logger.info("TOOL promo_tools.get_best_deals.success chars=%s", len(result))
        return result
    except RuntimeError as exc:
        logger.warning("TOOL promo_tools.get_best_deals.db_unavailable error=%s", exc)
        return "Hiện chưa cấu hình kết nối cơ sở dữ liệu để lấy ưu đãi tốt nhất."
    except Exception:
        logger.exception("TOOL promo_tools.get_best_deals.failed")
        return "Không thể tải danh sách ưu đãi tốt nhất lúc này."
