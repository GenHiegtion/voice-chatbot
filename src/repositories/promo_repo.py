"""Read-only promotion repository."""

from __future__ import annotations

from datetime import datetime
import logging

from sqlalchemy import and_, or_, select, text
from sqlalchemy.exc import SQLAlchemyError

from src.db_schema import Product, SaleOff

from .base_repo import ReadOnlyRepository
from .records import PromotionRecord

logger = logging.getLogger(__name__)


class PromotionRepository(ReadOnlyRepository):
    """Database queries for promotions tied to products."""

    async def _list_active_promotions_via_view(self, limit: int | None = None) -> list[PromotionRecord]:
        sql = """
            SELECT
              sale_off_id AS id,
              product_id,
              product_name,
              price AS product_price,
              discount,
              start_date,
              end_date
            FROM vw_product_active_deals
            ORDER BY discount DESC, product_name ASC
        """
        if limit is not None:
            sql += f"\nLIMIT {max(1, min(limit, 20))}"

        stmt = text(sql)
        async with self.session() as session:
            rows = (await session.execute(stmt)).all()

        return [
            PromotionRecord(
                id=int(row.id),
                product_id=int(row.product_id),
                product_name=str(row.product_name),
                product_price=row.product_price,
                discount=row.discount,
                start_date=row.start_date,
                end_date=row.end_date,
                is_active=True,
            )
            for row in rows
        ]

    @staticmethod
    def _active_filters(now: datetime):
        return (
            SaleOff.is_active.is_(True),
            Product.is_selling.is_(True),
            or_(SaleOff.start_date.is_(None), SaleOff.start_date <= now),
            or_(SaleOff.end_date.is_(None), SaleOff.end_date >= now),
        )

    async def _list_active_promotions_from_tables(self, check_time: datetime) -> list[PromotionRecord]:
        stmt = (
            select(
                SaleOff.id,
                SaleOff.product_id,
                SaleOff.discount,
                SaleOff.start_date,
                SaleOff.end_date,
                SaleOff.is_active,
                Product.name.label("product_name"),
                Product.price.label("product_price"),
            )
            .join(Product, Product.id == SaleOff.product_id)
            .where(and_(*self._active_filters(check_time)))
            .order_by(SaleOff.discount.desc(), Product.name.asc())
        )

        async with self.session() as session:
            rows = (await session.execute(stmt)).all()

        return [
            PromotionRecord(
                id=row.id,
                product_id=row.product_id,
                product_name=row.product_name,
                product_price=row.product_price,
                discount=row.discount,
                start_date=row.start_date,
                end_date=row.end_date,
                is_active=bool(row.is_active),
            )
            for row in rows
        ]

    async def list_active_promotions(self, now: datetime | None = None) -> list[PromotionRecord]:
        check_time = now or datetime.now()
        logger.info("REPO promo.list_active_promotions.start now=%s", check_time.isoformat())

        try:
            promotions = await self._list_active_promotions_via_view()
            logger.info("REPO promo.list_active_promotions.done source=view count=%s", len(promotions))
            return promotions
        except SQLAlchemyError as exc:
            logger.warning(
                "REPO promo.list_active_promotions.view_query_failed error=%s fallback=tables",
                type(exc).__name__,
            )

        promotions = await self._list_active_promotions_from_tables(check_time)
        logger.info("REPO promo.list_active_promotions.done source=tables count=%s", len(promotions))
        return promotions

    async def get_promotion_for_product(
        self,
        product_id: int,
        now: datetime | None = None,
    ) -> PromotionRecord | None:
        check_time = now or datetime.now()
        logger.info(
            "REPO promo.get_promotion_for_product.start product_id=%s now=%s",
            product_id,
            check_time.isoformat(),
        )

        try:
            stmt = text(
                """
                SELECT
                  sale_off_id AS id,
                  product_id,
                  product_name,
                  price AS product_price,
                  discount,
                  start_date,
                  end_date
                FROM vw_product_active_deals
                WHERE product_id = :product_id
                ORDER BY discount DESC
                LIMIT 1
                """
            )
            async with self.session() as session:
                row = (await session.execute(stmt, {"product_id": product_id})).first()

            if row:
                logger.info("REPO promo.get_promotion_for_product.done source=view found=true")
                return PromotionRecord(
                    id=int(row.id),
                    product_id=int(row.product_id),
                    product_name=str(row.product_name),
                    product_price=row.product_price,
                    discount=row.discount,
                    start_date=row.start_date,
                    end_date=row.end_date,
                    is_active=True,
                )

            logger.info("REPO promo.get_promotion_for_product.done source=view found=false")
            return None
        except SQLAlchemyError as exc:
            logger.warning(
                "REPO promo.get_promotion_for_product.view_query_failed error=%s fallback=tables",
                type(exc).__name__,
            )

        stmt = (
            select(
                SaleOff.id,
                SaleOff.product_id,
                SaleOff.discount,
                SaleOff.start_date,
                SaleOff.end_date,
                SaleOff.is_active,
                Product.name.label("product_name"),
                Product.price.label("product_price"),
            )
            .join(Product, Product.id == SaleOff.product_id)
            .where(and_(*self._active_filters(check_time), SaleOff.product_id == product_id))
            .order_by(SaleOff.discount.desc())
            .limit(1)
        )

        async with self.session() as session:
            row = (await session.execute(stmt)).first()

        if not row:
            logger.info("REPO promo.get_promotion_for_product.done source=tables found=false")
            return None

        logger.info("REPO promo.get_promotion_for_product.done source=tables found=true")
        return PromotionRecord(
            id=row.id,
            product_id=row.product_id,
            product_name=row.product_name,
            product_price=row.product_price,
            discount=row.discount,
            start_date=row.start_date,
            end_date=row.end_date,
            is_active=bool(row.is_active),
        )

    async def get_best_deals(self, limit: int = 5, now: datetime | None = None) -> list[PromotionRecord]:
        normalized_limit = max(1, min(limit, 20))
        logger.info("REPO promo.get_best_deals.start limit=%s", normalized_limit)

        try:
            deals = await self._list_active_promotions_via_view(limit=normalized_limit)
            logger.info("REPO promo.get_best_deals.done source=view count=%s", len(deals))
            return deals
        except SQLAlchemyError as exc:
            logger.warning(
                "REPO promo.get_best_deals.view_query_failed error=%s fallback=tables",
                type(exc).__name__,
            )

        deals = await self.list_active_promotions(now=now)
        result = deals[:normalized_limit]
        logger.info("REPO promo.get_best_deals.done source=tables count=%s", len(result))
        return result
