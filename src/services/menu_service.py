"""Business logic for menu-related data-team tools."""

from __future__ import annotations

import logging

from src.repositories.menu_repo import MenuRepository
from src.repositories.promo_repo import PromotionRepository
from src.skills.guard_skill import guard_out_of_scope
from src.skills.query_skill import extract_price_bounds, infer_category
from src.skills.response_skill import format_categories, format_product_detail, format_products

logger = logging.getLogger(__name__)


class MenuService:
    """Service layer for menu lookups and formatting."""

    def __init__(
        self,
        menu_repo: MenuRepository | None = None,
        promo_repo: PromotionRepository | None = None,
    ):
        self._menu_repo = menu_repo or MenuRepository()
        self._promo_repo = promo_repo or PromotionRepository()

    async def get_menu_categories(self) -> str:
        logger.info("SERVICE menu.get_menu_categories.start")
        categories = await self._menu_repo.list_categories()
        logger.info("SERVICE menu.get_menu_categories.repo_result count=%s", len(categories))
        return format_categories(categories)

    async def search_menu(
        self,
        query: str,
        *,
        category: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
    ) -> str:
        logger.info(
            "SERVICE menu.search_menu.start query=%s category=%s min_price=%s max_price=%s",
            query,
            category,
            min_price,
            max_price,
        )
        guard_message = guard_out_of_scope(query)
        if guard_message:
            logger.info("SERVICE menu.search_menu.guard_blocked")
            return guard_message

        logger.info("SERVICE menu.search_menu.call_skill skill=QuerySkill.extract_price_bounds")
        parsed_min, parsed_max = extract_price_bounds(query)
        logger.info("SERVICE menu.search_menu.call_skill skill=QuerySkill.infer_category")
        category_value = (category or "").strip() or infer_category(query)
        min_value = min_price if min_price and min_price > 0 else parsed_min
        max_value = max_price if max_price and max_price > 0 else parsed_max

        logger.info(
            "SERVICE menu.search_menu.skill_result category=%s min=%s max=%s",
            category_value,
            min_value,
            max_value,
        )

        products = await self._menu_repo.search_products(
            query=query,
            category=category_value,
            min_price=min_value,
            max_price=max_value,
            limit=20,
        )
        logger.info("SERVICE menu.search_menu.repo_result count=%s", len(products))

        title_parts = []
        if category_value:
            title_parts.append(f"danh mục {category_value}")
        if min_value or max_value:
            title_parts.append("lọc theo giá")
        title = "Kết quả tìm món" + (f" ({', '.join(title_parts)}):" if title_parts else ":")

        return format_products(products, title=title)

    async def get_dish_details(self, dish_name_or_id: str) -> str:
        logger.info("SERVICE menu.get_dish_details.start ref=%s", dish_name_or_id)
        guard_message = guard_out_of_scope(dish_name_or_id)
        if guard_message:
            logger.info("SERVICE menu.get_dish_details.guard_blocked")
            return guard_message

        product = await self._menu_repo.get_product_by_id_or_name(dish_name_or_id)
        if product is None:
            logger.info("SERVICE menu.get_dish_details.product_not_found ref=%s", dish_name_or_id)
            return f"Không tìm thấy món '{dish_name_or_id}' trong danh sách đang bán."

        promotion = await self._promo_repo.get_promotion_for_product(product.id)
        logger.info("SERVICE menu.get_dish_details.promotion_found=%s", promotion is not None)
        return format_product_detail(product, promotion)

    async def get_dishes_by_category(self, category: str) -> str:
        logger.info("SERVICE menu.get_dishes_by_category.start category=%s", category)
        products = await self._menu_repo.get_products_by_category(category)
        logger.info("SERVICE menu.get_dishes_by_category.repo_result count=%s", len(products))
        return format_products(products, title=f"Các món trong danh mục '{category}':")
