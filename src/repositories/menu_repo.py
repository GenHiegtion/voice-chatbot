"""Read-only menu repository."""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import SQLAlchemyError

from src.db_schema import Catalog, Product

from .base_repo import ReadOnlyRepository
from .records import CategoryRecord, ProductRecord

logger = logging.getLogger(__name__)


class MenuRepository(ReadOnlyRepository):
    """Database queries for menu and product information."""

    async def _search_products_via_view(
        self,
        *,
        query: str | None,
        category: str | None,
        min_price: int | None,
        max_price: int | None,
        limit: int,
    ) -> list[ProductRecord]:
        sql_parts = [
            "SELECT id, name, description, price, catalog_id, catalog_name",
            "FROM vw_sell_products",
            "WHERE 1=1",
        ]
        params: dict[str, object] = {}

        if category:
            sql_parts.append("AND LOWER(catalog_name) LIKE :category")
            params["category"] = f"%{category.strip().lower()}%"

        if query:
            sql_parts.append(
                "AND (LOWER(name) LIKE :query OR LOWER(COALESCE(description, '')) LIKE :query OR LOWER(catalog_name) LIKE :query)"
            )
            params["query"] = f"%{query.strip().lower()}%"

        if min_price is not None:
            sql_parts.append("AND price >= :min_price")
            params["min_price"] = Decimal(min_price)

        if max_price is not None:
            sql_parts.append("AND price <= :max_price")
            params["max_price"] = Decimal(max_price)

        sql_parts.append("ORDER BY name ASC")
        sql_parts.append(f"LIMIT {max(1, min(limit, 100))}")

        stmt = text("\n".join(sql_parts))
        async with self.session() as session:
            rows = (await session.execute(stmt, params)).all()

        return [
            ProductRecord(
                id=int(row.id),
                name=str(row.name),
                description=str(row.description or ""),
                price=Decimal(row.price),
                is_selling=True,
                category_id=int(row.catalog_id),
                category_name=str(row.catalog_name),
            )
            for row in rows
        ]

    async def _get_product_by_id_or_name_via_view(self, dish_name_or_id: str) -> ProductRecord | None:
        ref = dish_name_or_id.strip()
        if not ref:
            return None

        if ref.isdigit():
            stmt = text(
                """
                SELECT id, name, description, price, catalog_id, catalog_name
                FROM vw_sell_products
                WHERE id = :id
                LIMIT 1
                """
            )
            params = {"id": int(ref)}
        else:
            stmt = text(
                """
                SELECT id, name, description, price, catalog_id, catalog_name
                FROM vw_sell_products
                WHERE LOWER(name) LIKE :query
                ORDER BY name ASC
                LIMIT 1
                """
            )
            params = {"query": f"%{ref.lower()}%"}

        async with self.session() as session:
            row = (await session.execute(stmt, params)).first()

        if not row:
            return None

        category_id = getattr(row, "catalog_id", getattr(row, "category_id", None))
        category_name = getattr(row, "catalog_name", getattr(row, "category_name", ""))

        return ProductRecord(
            id=int(row.id),
            name=str(row.name),
            description=str(row.description or ""),
            price=Decimal(row.price),
            is_selling=True,
            category_id=int(category_id or 0),
            category_name=str(category_name),
        )

    async def list_categories(self) -> list[CategoryRecord]:
        logger.info("REPO menu.list_categories.start")
        stmt = select(Catalog.id, Catalog.name).order_by(Catalog.name.asc())
        async with self.session() as session:
            rows = (await session.execute(stmt)).all()
        logger.info("REPO menu.list_categories.done count=%s", len(rows))

        return [CategoryRecord(id=row.id, name=row.name) for row in rows]

    async def search_products(
        self,
        *,
        query: str | None = None,
        category: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        limit: int = 20,
    ) -> list[ProductRecord]:
        logger.info(
            "REPO menu.search_products.start query=%s category=%s min_price=%s max_price=%s limit=%s",
            query,
            category,
            min_price,
            max_price,
            limit,
        )
        try:
            products = await self._search_products_via_view(
                query=query,
                category=category,
                min_price=min_price,
                max_price=max_price,
                limit=limit,
            )
            logger.info("REPO menu.search_products.done source=view count=%s", len(products))
            return products
        except SQLAlchemyError as exc:
            logger.warning(
                "REPO menu.search_products.view_query_failed error=%s fallback=tables",
                type(exc).__name__,
            )

        stmt = (
            select(
                Product.id,
                Product.name,
                Product.description,
                Product.price,
                Product.is_selling,
                Catalog.id.label("category_id"),
                Catalog.name.label("category_name"),
            )
            .join(Catalog, Catalog.id == Product.catalog_id)
            .where(Product.is_selling.is_(True))
        )

        if category:
            category_pattern = f"%{category.strip().lower()}%"
            stmt = stmt.where(func.lower(Catalog.name).like(category_pattern))

        if query:
            pattern = f"%{query.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Product.name).like(pattern),
                    func.lower(func.coalesce(Product.description, "")).like(pattern),
                    func.lower(Catalog.name).like(pattern),
                )
            )

        if min_price is not None:
            stmt = stmt.where(Product.price >= Decimal(min_price))

        if max_price is not None:
            stmt = stmt.where(Product.price <= Decimal(max_price))

        stmt = stmt.order_by(Product.name.asc()).limit(max(1, min(limit, 100)))

        async with self.session() as session:
            rows = (await session.execute(stmt)).all()

        logger.info("REPO menu.search_products.done source=tables count=%s", len(rows))

        return [
            ProductRecord(
                id=row.id,
                name=row.name,
                description=row.description or "",
                price=row.price,
                is_selling=bool(row.is_selling),
                category_id=row.category_id,
                category_name=row.category_name,
            )
            for row in rows
        ]

    async def get_product_by_id_or_name(self, dish_name_or_id: str) -> ProductRecord | None:
        logger.info("REPO menu.get_product_by_id_or_name.start ref=%s", dish_name_or_id)
        ref = (dish_name_or_id or "").strip()
        if not ref:
            logger.info("REPO menu.get_product_by_id_or_name.empty_ref")
            return None

        try:
            product = await self._get_product_by_id_or_name_via_view(ref)
            if product is not None:
                logger.info("REPO menu.get_product_by_id_or_name.done source=view found=true")
                return product
            logger.info("REPO menu.get_product_by_id_or_name.done source=view found=false")
            return None
        except SQLAlchemyError as exc:
            logger.warning(
                "REPO menu.get_product_by_id_or_name.view_query_failed error=%s fallback=tables",
                type(exc).__name__,
            )

        stmt = (
            select(
                Product.id,
                Product.name,
                Product.description,
                Product.price,
                Product.is_selling,
                Catalog.id.label("category_id"),
                Catalog.name.label("category_name"),
            )
            .join(Catalog, Catalog.id == Product.catalog_id)
            .where(Product.is_selling.is_(True))
        )

        if ref.isdigit():
            stmt = stmt.where(Product.id == int(ref))
        else:
            pattern = f"%{ref.lower()}%"
            stmt = stmt.where(func.lower(Product.name).like(pattern)).order_by(Product.name.asc())

        stmt = stmt.limit(1)

        async with self.session() as session:
            row = (await session.execute(stmt)).first()

        if not row:
            logger.info("REPO menu.get_product_by_id_or_name.done source=tables found=false")
            return None

        logger.info("REPO menu.get_product_by_id_or_name.done source=tables found=true")
        return ProductRecord(
            id=row.id,
            name=row.name,
            description=row.description or "",
            price=row.price,
            is_selling=bool(row.is_selling),
            category_id=row.category_id,
            category_name=row.category_name,
        )

    async def get_products_by_category(self, category: str, limit: int = 20) -> list[ProductRecord]:
        logger.info("REPO menu.get_products_by_category.start category=%s limit=%s", category, limit)
        return await self.search_products(category=category, limit=limit)
