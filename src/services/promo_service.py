"""Business logic for promotion-related data-team tools."""

from __future__ import annotations

import logging

from src.repositories.menu_repo import MenuRepository
from src.repositories.promo_repo import PromotionRepository
from src.skills.guard_skill import guard_out_of_scope
from src.skills.response_skill import format_promotion_for_dish, format_promotions

logger = logging.getLogger(__name__)


class PromotionService:
    """Service layer for active promotions and dish-level discounts."""

    def __init__(
        self,
        promo_repo: PromotionRepository | None = None,
        menu_repo: MenuRepository | None = None,
    ):
        self._promo_repo = promo_repo or PromotionRepository()
        self._menu_repo = menu_repo or MenuRepository()

    async def get_active_promotions(self) -> str:
        logger.info("SERVICE promotion.get_active_promotions.start")
        promotions = await self._promo_repo.list_active_promotions()
        logger.info("SERVICE promotion.get_active_promotions.repo_result count=%s", len(promotions))
        return format_promotions(promotions, title="Ưu đãi đang áp dụng:")

    async def check_promotion_for_dish(self, dish_name_or_id: str) -> str:
        logger.info("SERVICE promotion.check_for_dish.start ref=%s", dish_name_or_id)
        guard_message = guard_out_of_scope(dish_name_or_id)
        if guard_message:
            logger.info("SERVICE promotion.check_for_dish.guard_blocked")
            return guard_message

        product = await self._menu_repo.get_product_by_id_or_name(dish_name_or_id)
        if product is None:
            logger.info("SERVICE promotion.check_for_dish.product_not_found ref=%s", dish_name_or_id)
            return f"Không tìm thấy món '{dish_name_or_id}' trong danh sách đang bán."

        promotion = await self._promo_repo.get_promotion_for_product(product.id)
        if promotion is None:
            logger.info("SERVICE promotion.check_for_dish.no_active_promotion product_id=%s", product.id)
            return f"Món {product.name} hiện chưa có ưu đãi trong thời điểm này."

        logger.info("SERVICE promotion.check_for_dish.promotion_found product_id=%s", product.id)
        return format_promotion_for_dish(product, promotion)

    async def get_best_deals(self, limit: int = 5) -> str:
        normalized_limit = max(1, min(limit, 20))
        logger.info("SERVICE promotion.get_best_deals.start limit=%s", normalized_limit)
        promotions = await self._promo_repo.get_best_deals(limit=normalized_limit)
        logger.info("SERVICE promotion.get_best_deals.repo_result count=%s", len(promotions))
        return format_promotions(promotions, title=f"Top {normalized_limit} ưu đãi tốt nhất:")
