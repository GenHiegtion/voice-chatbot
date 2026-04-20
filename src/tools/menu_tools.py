"""Mock menu tools for the menu agent.

These tools simulate a menu database. Replace with real API calls
when the App Service is available.
"""

from functools import lru_cache

from langchain_core.tools import tool

# --- Mock data ---
MOCK_MENU = {
    "categories": [
        {"id": "pho", "name": "Phở", "description": "Các loại phở truyền thống"},
        {"id": "com", "name": "Cơm", "description": "Các món cơm"},
        {"id": "bun", "name": "Bún", "description": "Các loại bún"},
        {"id": "drink", "name": "Đồ uống", "description": "Nước giải khát & trà"},
        {"id": "dessert", "name": "Tráng miệng", "description": "Chè & bánh"},
    ],
    "dishes": [
        {
            "id": "pho-bo",
            "name": "Phở Bò",
            "category": "pho",
            "price": 55000,
            "description": "Phở bò truyền thống với nước dùng hầm xương 12 tiếng, thịt bò tái lăn",
            "ingredients": ["bánh phở", "thịt bò", "hành lá", "rau thơm", "giá đỗ"],
            "is_available": True,
        },
        {
            "id": "pho-ga",
            "name": "Phở Gà",
            "category": "pho",
            "price": 50000,
            "description": "Phở gà nước trong, thịt gà ta xé nhỏ",
            "ingredients": ["bánh phở", "thịt gà", "hành lá", "rau thơm", "giá đỗ"],
            "is_available": True,
        },
        {
            "id": "com-suon",
            "name": "Cơm Sườn Nướng",
            "category": "com",
            "price": 60000,
            "description": "Cơm trắng với sườn heo nướng mật ong, kèm rau sống và canh",
            "ingredients": ["cơm", "sườn heo", "rau sống", "nước mắm", "đồ chua"],
            "is_available": True,
        },
        {
            "id": "com-ga",
            "name": "Cơm Gà Xối Mỡ",
            "category": "com",
            "price": 55000,
            "description": "Cơm gà xối mỡ giòn rụm, kèm rau sống và nước mắm tỏi ớt",
            "ingredients": ["cơm", "đùi gà", "rau sống", "nước mắm tỏi ớt"],
            "is_available": True,
        },
        {
            "id": "bun-bo-hue",
            "name": "Bún Bò Huế",
            "category": "bun",
            "price": 55000,
            "description": "Bún bò Huế cay nồng đặc trưng với chả cua và giò heo",
            "ingredients": ["bún", "thịt bò", "giò heo", "chả cua", "rau sống"],
            "is_available": True,
        },
        {
            "id": "bun-cha",
            "name": "Bún Chả Hà Nội",
            "category": "bun",
            "price": 50000,
            "description": "Bún chả với chả viên và chả miếng nướng than hoa",
            "ingredients": ["bún", "chả viên", "chả miếng", "nước mắm chua ngọt", "rau sống"],
            "is_available": False,
        },
        {
            "id": "tra-da",
            "name": "Trà Đá",
            "category": "drink",
            "price": 5000,
            "description": "Trà xanh đá mát lạnh",
            "ingredients": ["trà xanh", "đá"],
            "is_available": True,
        },
        {
            "id": "nuoc-cam",
            "name": "Nước Cam Tươi",
            "category": "drink",
            "price": 25000,
            "description": "Nước cam ép tươi 100%",
            "ingredients": ["cam tươi"],
            "is_available": True,
        },
        {
            "id": "cafe-sua-da",
            "name": "Cà Phê Sữa Đá",
            "category": "drink",
            "price": 25000,
            "description": "Cà phê phin pha sữa đặc, thêm đá",
            "ingredients": ["cà phê", "sữa đặc", "đá"],
            "is_available": True,
        },
        {
            "id": "che-thai",
            "name": "Chè Thái",
            "category": "dessert",
            "price": 20000,
            "description": "Chè Thái truyền thống với nhiều loại trái cây và nước cốt dừa",
            "ingredients": ["nước cốt dừa", "mít", "vải", "thạch", "đá bào"],
            "is_available": True,
        },
    ],
}

_CATEGORY_MAP = {
    "phở": "pho",
    "pho": "pho",
    "cơm": "com",
    "com": "com",
    "bún": "bun",
    "bun": "bun",
    "đồ uống": "drink",
    "nước": "drink",
    "drink": "drink",
    "tráng miệng": "dessert",
    "chè": "dessert",
    "dessert": "dessert",
}


@lru_cache(maxsize=2048)
def _format_price(price: int) -> str:
    """Format price in VND."""
    return f"{price:,}đ"


@lru_cache(maxsize=1)
def _build_categories_text() -> str:
    categories = MOCK_MENU["categories"]
    result = "📋 Danh mục thực đơn:\n"
    for cat in categories:
        result += f"  • {cat['name']}: {cat['description']}\n"
    return result


@tool
def get_menu_categories() -> str:
    """Lấy danh sách các danh mục món ăn trong thực đơn."""
    return _build_categories_text()


@tool
def search_menu(query: str) -> str:
    """Tìm kiếm món ăn trong thực đơn theo tên hoặc mô tả.

    Args:
        query: Từ khóa tìm kiếm (tên món, nguyên liệu, loại món)
    """
    query_lower = query.lower()
    results = []

    for dish in MOCK_MENU["dishes"]:
        if (
            query_lower in dish["name"].lower()
            or query_lower in dish["description"].lower()
            or query_lower in dish["category"].lower()
            or any(query_lower in ing.lower() for ing in dish["ingredients"])
        ):
            status = "✅ Còn" if dish["is_available"] else "❌ Hết"
            results.append(
                f"  • {dish['name']} - {_format_price(dish['price'])} [{status}]")

    if not results:
        return f"Không tìm thấy món nào phù hợp với '{query}'."

    return f"🔍 Kết quả tìm kiếm cho '{query}':\n" + "\n".join(results)


@tool
def get_dish_details(dish_name: str) -> str:
    """Lấy thông tin chi tiết của một món ăn cụ thể.

    Args:
        dish_name: Tên món ăn cần xem chi tiết
    """
    dish_name_lower = dish_name.lower()

    for dish in MOCK_MENU["dishes"]:
        if dish_name_lower in dish["name"].lower():
            status = "✅ Còn hàng" if dish["is_available"] else "❌ Tạm hết"
            ingredients = ", ".join(dish["ingredients"])
            return (
                f"🍽️ {dish['name']}\n"
                f"  💰 Giá: {_format_price(dish['price'])}\n"
                f"  📝 Mô tả: {dish['description']}\n"
                f"  🥗 Nguyên liệu: {ingredients}\n"
                f"  📦 Trạng thái: {status}"
            )

    return f"Không tìm thấy món '{dish_name}' trong thực đơn."


@tool
def get_dishes_by_category(category: str) -> str:
    """Lấy danh sách món ăn theo danh mục.

    Args:
        category: Tên danh mục (phở, cơm, bún, đồ uống, tráng miệng)
    """
    category_lower = category.lower()

    cat_id = _CATEGORY_MAP.get(category_lower, category_lower)
    dishes = [d for d in MOCK_MENU["dishes"] if d["category"] == cat_id]

    if not dishes:
        return f"Không tìm thấy danh mục '{category}'."

    result = f"📋 Các món {category}:\n"
    for dish in dishes:
        status = "✅" if dish["is_available"] else "❌ Hết"
        result += f"  • {dish['name']} - {_format_price(dish['price'])} {status}\n"
    return result
