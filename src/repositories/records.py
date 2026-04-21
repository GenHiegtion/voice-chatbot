"""Read models returned by repository layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(slots=True)
class CategoryRecord:
    id: int
    name: str


@dataclass(slots=True)
class ProductRecord:
    id: int
    name: str
    description: str
    price: Decimal
    is_selling: bool
    category_id: int
    category_name: str


@dataclass(slots=True)
class PromotionRecord:
    id: int
    product_id: int
    product_name: str
    product_price: Decimal
    discount: Decimal
    start_date: datetime | None
    end_date: datetime | None
    is_active: bool
