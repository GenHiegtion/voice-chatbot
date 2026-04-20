"""Mock promotion tools for the promotion agent.

These tools simulate promotion/discount data. Replace with real API calls
when the App Service is available.
"""

from functools import lru_cache

from langchain_core.tools import tool

# --- Mock data ---
MOCK_PROMOTIONS = [
    {
        "id": "promo-1",
        "name": "Giảm 20% Phở",
        "description": "Giảm 20% cho tất cả các loại phở từ thứ 2 đến thứ 6",
        "discount_type": "percentage",
        "discount_value": 20,
        "applicable_items": ["phở bò", "phở gà"],
        "conditions": "Áp dụng từ thứ 2 đến thứ 6, 11h-14h",
        "is_active": True,
    },
    {
        "id": "promo-2",
        "name": "Combo Trưa Tiết Kiệm",
        "description": "Mua 1 phần cơm + 1 đồ uống chỉ với 65,000đ (tiết kiệm 15,000đ)",
        "discount_type": "combo",
        "discount_value": 15000,
        "applicable_items": ["cơm sườn nướng", "cơm gà xối mỡ", "trà đá", "nước cam tươi"],
        "conditions": "Áp dụng hàng ngày, 11h-14h",
        "is_active": True,
    },
    {
        "id": "promo-3",
        "name": "Miễn phí giao hàng",
        "description": "Miễn phí giao hàng cho đơn từ 100,000đ",
        "discount_type": "free_shipping",
        "discount_value": 0,
        "applicable_items": [],
        "conditions": "Đơn hàng tối thiểu 100,000đ, bán kính 5km",
        "is_active": True,
    },
    {
        "id": "promo-4",
        "name": "Giảm 10% đơn đầu tiên",
        "description": "Khách hàng mới được giảm 10% cho đơn hàng đầu tiên",
        "discount_type": "percentage",
        "discount_value": 10,
        "applicable_items": [],
        "conditions": "Chỉ áp dụng cho khách hàng mới, tối đa giảm 30,000đ",
        "is_active": True,
    },
    {
        "id": "promo-5",
        "name": "Happy Hour Đồ Uống",
        "description": "Mua 1 tặng 1 tất cả đồ uống từ 14h-17h hàng ngày",
        "discount_type": "buy_one_get_one",
        "discount_value": 0,
        "applicable_items": ["trà đá", "nước cam tươi", "cà phê sữa đá"],
        "conditions": "Áp dụng từ 14h-17h hàng ngày",
        "is_active": True,
    },
]

MOCK_COUPONS = {
    "NEWUSER10": {"discount": 10, "type": "percentage", "max_discount": 30000, "is_valid": True},
    "FREESHIP": {"discount": 0, "type": "free_shipping", "max_discount": 0, "is_valid": True},
    "PHO20": {"discount": 20, "type": "percentage", "max_discount": 20000, "is_valid": True},
    "EXPIRED50": {"discount": 50, "type": "percentage", "max_discount": 100000, "is_valid": False},
}


@lru_cache(maxsize=1)
def _get_active_promotions_data() -> tuple[dict, ...]:
    return tuple(p for p in MOCK_PROMOTIONS if p["is_active"])


@lru_cache(maxsize=1)
def _build_active_promotions_text() -> str:
    active = _get_active_promotions_data()
    if not active:
        return "Hiện tại không có chương trình khuyến mãi nào."

    result = "🎉 Khuyến mãi đang có:\n"
    for promo in active:
        result += f"\n  🏷️ {promo['name']}\n"
        result += f"     {promo['description']}\n"
        result += f"     📌 Điều kiện: {promo['conditions']}\n"
    return result


@tool
def get_active_promotions() -> str:
    """Lấy danh sách các chương trình khuyến mãi đang hoạt động."""
    return _build_active_promotions_text()


@tool
def check_promotion_for_dish(dish_name: str) -> str:
    """Kiểm tra khuyến mãi áp dụng cho một món ăn cụ thể.

    Args:
        dish_name: Tên món ăn cần kiểm tra khuyến mãi
    """
    dish_name_lower = dish_name.lower()
    applicable = []

    for promo in _get_active_promotions_data():
        # Empty applicable_items means applies to all
        if not promo["applicable_items"] or any(
            dish_name_lower in item for item in promo["applicable_items"]
        ):
            applicable.append(promo)

    if not applicable:
        return f"Hiện tại không có khuyến mãi nào áp dụng cho '{dish_name}'."

    result = f"🎉 Khuyến mãi cho '{dish_name}':\n"
    for promo in applicable:
        result += f"  🏷️ {promo['name']}: {promo['description']}\n"
        result += f"     📌 {promo['conditions']}\n"
    return result


@tool
def check_coupon(coupon_code: str) -> str:
    """Kiểm tra mã giảm giá có hợp lệ không.

    Args:
        coupon_code: Mã coupon cần kiểm tra
    """
    code = coupon_code.upper()
    coupon = MOCK_COUPONS.get(code)

    if not coupon:
        return f"❌ Mã '{coupon_code}' không tồn tại."

    if not coupon["is_valid"]:
        return f"❌ Mã '{coupon_code}' đã hết hạn hoặc không còn hiệu lực."

    if coupon["type"] == "percentage":
        desc = f"Giảm {coupon['discount']}%"
        if coupon["max_discount"] > 0:
            desc += f" (tối đa {coupon['max_discount']:,}đ)"
    elif coupon["type"] == "free_shipping":
        desc = "Miễn phí giao hàng"
    else:
        desc = f"Giảm {coupon['discount']:,}đ"

    return f"✅ Mã '{code}' hợp lệ! {desc}"
