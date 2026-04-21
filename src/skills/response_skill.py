"""Response formatting helpers for data-team outputs."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from src.repositories.records import CategoryRecord, ProductRecord, PromotionRecord


def format_price(amount: Decimal | int | float) -> str:
    """Format VND amount with Vietnamese thousands separator."""
    value = Decimal(str(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{int(value):,}đ".replace(",", ".")


def _format_time(value: datetime | None) -> str:
    if value is None:
        return "không giới hạn"
    return value.strftime("%d/%m/%Y %H:%M")


def discounted_price(base_price: Decimal, discount_percent: Decimal) -> Decimal:
    """Calculate discounted price from percentage discount."""
    clamped_discount = max(Decimal("0"), min(Decimal("100"), Decimal(discount_percent)))
    ratio = (Decimal("100") - clamped_discount) / Decimal("100")
    return (Decimal(base_price) * ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def format_categories(categories: list[CategoryRecord]) -> str:
    if not categories:
        return "Hiện chưa có danh mục món ăn nào đang hiển thị."

    lines = ["Danh mục hiện có:"]
    for item in categories:
        lines.append(f"- {item.name}")
    return "\n".join(lines)


def format_products(products: list[ProductRecord], *, title: str | None = None) -> str:
    if not products:
        return "Không tìm thấy món phù hợp với yêu cầu của bạn."

    lines = [title or "Kết quả món ăn:"]
    for dish in products:
        lines.append(f"- {dish.name} ({dish.category_name}): {format_price(dish.price)}")
    return "\n".join(lines)


def format_product_detail(product: ProductRecord, promotion: PromotionRecord | None = None) -> str:
    lines = [
        f"{product.name}",
        f"- Danh mục: {product.category_name}",
        f"- Giá niêm yết: {format_price(product.price)}",
    ]

    if promotion is not None:
        final_price = discounted_price(product.price, promotion.discount)
        lines.extend(
            [
                f"- Ưu đãi hiện tại: giảm {promotion.discount}%",
                f"- Giá sau ưu đãi: {format_price(final_price)}",
                (
                    "- Thời gian áp dụng: "
                    f"{_format_time(promotion.start_date)} đến {_format_time(promotion.end_date)}"
                ),
            ]
        )

    if product.description:
        lines.append(f"- Mô tả: {product.description}")

    return "\n".join(lines)


def format_promotions(promotions: list[PromotionRecord], *, title: str) -> str:
    if not promotions:
        return "Hiện tại chưa có ưu đãi nào phù hợp."

    lines = [title]
    for promo in promotions:
        lines.extend(
            [
                f"- {promo.product_name}: giảm {promo.discount}%",
                f"  Giá hiện tại: {format_price(discounted_price(promo.product_price, promo.discount))}",
                f"  Hiệu lực: {_format_time(promo.start_date)} đến {_format_time(promo.end_date)}",
            ]
        )
    return "\n".join(lines)


def format_promotion_for_dish(product: ProductRecord, promotion: PromotionRecord) -> str:
    final_price = discounted_price(product.price, promotion.discount)
    return "\n".join(
        [
            f"Món {product.name} đang có ưu đãi giảm {promotion.discount}%.",
            f"- Giá niêm yết: {format_price(product.price)}",
            f"- Giá sau ưu đãi: {format_price(final_price)}",
            f"- Hiệu lực: {_format_time(promotion.start_date)} đến {_format_time(promotion.end_date)}",
        ]
    )
