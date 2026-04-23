"""Mock order tools for the order agent.

These tools simulate cart and order management. Replace with real API calls
when the App Service is available.
"""

import time
from functools import lru_cache

from langchain_core.tools import tool

from src.config import get_settings
from src.repositories.menu_repo import MenuRepository

_menu_repo = MenuRepository()

# --- In-memory session carts (mock) ---
_carts: dict[str, dict] = {}
_last_cleanup_at = 0.0


def _cleanup_expired_carts() -> None:
    """Clean up stale carts to avoid unbounded memory growth."""
    global _last_cleanup_at

    now = time.time()
    # Run cleanup at most once per minute.
    if now - _last_cleanup_at < 60:
        return

    ttl_seconds = max(60, get_settings().cart_ttl_seconds)
    expired_session_ids = [
        session_id
        for session_id, cart_data in _carts.items()
        if now - float(cart_data.get("last_access", now)) > ttl_seconds
    ]

    for session_id in expired_session_ids:
        _carts.pop(session_id, None)

    _last_cleanup_at = now


def _get_cart(session_id: str) -> list[dict]:
    """Get or create cart for a session."""
    _cleanup_expired_carts()

    if session_id not in _carts:
        _carts[session_id] = {
            "items": [],
            "last_access": time.time(),
        }

    _carts[session_id]["last_access"] = time.time()
    return _carts[session_id]["items"]


@lru_cache(maxsize=2048)
def _format_price(price: int) -> str:
    return f"{price:,}đ"


# Simple dish lookup for validation
_DISH_PRICES = {
    "phở bò": 55000,
    "phở gà": 50000,
    "cơm sườn nướng": 60000,
    "cơm gà xối mỡ": 55000,
    "bún bò huế": 55000,
    "bún chả hà nội": 50000,
    "trà đá": 5000,
    "nước cam tươi": 25000,
    "cà phê sữa đá": 25000,
    "chè thái": 20000,
}


def _find_dish(name: str) -> tuple[str, int] | None:
    """Find dish by partial name match."""
    name_lower = name.lower()
    for dish_name, price in _DISH_PRICES.items():
        if name_lower in dish_name or dish_name in name_lower:
            return dish_name, price
    return None


@tool
def add_to_cart(session_id: str, dish_name: str, quantity: int = 1) -> str:
    """Thêm món ăn vào giỏ hàng.

    Args:
        session_id: ID phiên chat của người dùng
        dish_name: Tên món ăn cần thêm
        quantity: Số lượng (mặc định 1)
    """
    if quantity <= 0:
        return "❌ Số lượng phải lớn hơn 0."

    # Look up the actual dish in the database
    import asyncio
    try:
        # Since tools can be called from async contexts, we need to safely run this
        loop = asyncio.get_event_loop()
        product = loop.run_until_complete(_menu_repo.get_product_by_id_or_name(dish_name))
    except Exception:
        # Fallback if there's an issue with the event loop
        product = None

    if not product:
        return f"❌ Không tìm thấy món '{dish_name}' trong thực đơn. Vui lòng kiểm tra lại tên món."

    actual_name = product.name
    price = int(product.price)
    
    try:
        loop = asyncio.get_event_loop()
        image_url = loop.run_until_complete(_menu_repo.get_product_image_url(product.id)) or ""
    except Exception:
        image_url = ""

    cart = _get_cart(session_id)

    # Check if dish already in cart
    for item in cart:
        if item["id"] == str(product.id):
            item["quantity"] += quantity
            return (
                f"✅ Đã cập nhật: {actual_name.title()} x{item['quantity']} "
                f"({_format_price(price * item['quantity'])})"
            )

    cart.append({
        "id": str(product.id),
        "name": actual_name, 
        "price": price, 
        "quantity": quantity,
        "url": image_url
    })
    return f"✅ Đã thêm: {actual_name.title()} x{quantity} ({_format_price(price * quantity)})"


@tool
def remove_from_cart(session_id: str, dish_name: str) -> str:
    """Xóa một món ăn khỏi giỏ hàng.

    Args:
        session_id: ID phiên chat của người dùng
        dish_name: Tên món ăn cần xóa
    """
    cart = _get_cart(session_id)
    dish_name_lower = dish_name.lower()

    for i, item in enumerate(cart):
        if dish_name_lower in item["name"] or item["name"] in dish_name_lower:
            removed = cart.pop(i)
            return f"✅ Đã xóa {removed['name'].title()} khỏi giỏ hàng."

    return f"❌ Không tìm thấy '{dish_name}' trong giỏ hàng."


@tool
def view_cart(session_id: str) -> str:
    """Xem nội dung giỏ hàng hiện tại.

    Args:
        session_id: ID phiên chat của người dùng
    """
    cart = _get_cart(session_id)

    if not cart:
        return "🛒 Giỏ hàng trống. Bạn chưa thêm món nào."

    result = "🛒 Giỏ hàng của bạn:\n"
    total = 0
    for item in cart:
        subtotal = item["price"] * item["quantity"]
        total += subtotal
        result += f"  • {item['name'].title()} x{item['quantity']} — {_format_price(subtotal)}\n"
    result += f"\n💰 Tổng cộng: {_format_price(total)}"
    return result


@tool
def update_cart_quantity(session_id: str, dish_name: str, quantity: int) -> str:
    """Cập nhật số lượng của một món trong giỏ hàng.

    Args:
        session_id: ID phiên chat của người dùng
        dish_name: Tên món ăn cần cập nhật
        quantity: Số lượng mới (đặt 0 để xóa)
    """
    if quantity < 0:
        return "❌ Số lượng không được âm."

    cart = _get_cart(session_id)
    dish_name_lower = dish_name.lower()

    for i, item in enumerate(cart):
        if dish_name_lower in item["name"] or item["name"] in dish_name_lower:
            if quantity <= 0:
                removed = cart.pop(i)
                return f"✅ Đã xóa {removed['name'].title()} khỏi giỏ hàng."
            item["quantity"] = quantity
            return (
                f"✅ Đã cập nhật: {item['name'].title()} x{quantity} "
                f"({_format_price(item['price'] * quantity)})"
            )

    return f"❌ Không tìm thấy '{dish_name}' trong giỏ hàng."


@tool
def place_order(session_id: str, delivery_address: str = "", note: str = "") -> str:
    """Xác nhận đặt hàng với giỏ hàng hiện tại.

    Args:
        session_id: ID phiên chat của người dùng
        delivery_address: Địa chỉ giao hàng
        note: Ghi chú cho đơn hàng (ví dụ: không hành, ít cay)
    """
    cart = _get_cart(session_id)

    if not cart:
        return "❌ Giỏ hàng trống. Vui lòng thêm món trước khi đặt hàng."

    total = sum(item["price"] * item["quantity"] for item in cart)
    items_str = ", ".join(
        f"{item['name'].title()} x{item['quantity']}" for item in cart)

    # Clear the cart after ordering
    _carts.pop(session_id, None)

    result = (
        f"✅ Đặt hàng thành công!\n"
        f"  📦 Đơn hàng: {items_str}\n"
        f"  💰 Tổng tiền: {_format_price(total)}\n"
    )
    if delivery_address:
        result += f"  📍 Giao đến: {delivery_address}\n"
    if note:
        result += f"  📝 Ghi chú: {note}\n"
    result += f"  ⏱️ Thời gian dự kiến: 25-35 phút"

    return result
