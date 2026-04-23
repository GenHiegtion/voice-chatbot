"""Menu agent for handling menu-related queries."""

from __future__ import annotations

import logging
import re
import time

from langchain_core.messages import AIMessage
from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent

from src.agents.state import AgentState
from src.tools import menu_tools

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Deterministic add-to-cart intent detection
# -----------------------------------------------------------------------
_ADD_KEYWORDS = [
    "thêm", "thêm vào", "order", "đặt món", "cho tôi", "cho mình",
    "mua", "lấy cho", "gọi món", "muốn thêm", "muốn mua", "muốn order",
    "add", "muốn đặt",
]
_QUANTITY_PATTERN = re.compile(r"(\d+)\s*(?:phần|ly|tô|bát|đĩa|cái|suất|con|cái)?", re.IGNORECASE)


def _detect_add_intent(user_text: str) -> bool:
    """Return True if user message clearly requests adding to cart."""
    text_lower = user_text.lower()
    return any(k in text_lower for k in _ADD_KEYWORDS)


def _extract_quantity(user_text: str) -> int:
    """Extract quantity from user message. Default 1."""
    m = _QUANTITY_PATTERN.search(user_text)
    if m:
        return max(1, int(m.group(1)))
    return 1


def _extract_dish_query(user_text: str) -> str:
    """Extract the dish name/query from user text, removing add-keywords and quantity."""
    text = user_text.lower()
    # Remove common filler prefixes
    for kw in _ADD_KEYWORDS:
        text = text.replace(kw, " ")
    # Remove quantity digits
    text = _QUANTITY_PATTERN.sub(" ", text)
    # Remove trailing add-to-cart suffixes and filler words
    text = re.sub(r"vào giỏ hàng|vào giỏ|vào cart", "", text)
    text = re.sub(r"\b(cho tôi|cho mình|cho em|cho anh|cho chị|nữa|với|nhé|nha|đi)\b", " ", text)
    return text.strip()


MENU_AGENT_PROMPT = """You are the restaurant menu specialist assistant. Your responsibilities are to help users:

- Browse menu categories
- Search dishes by name or ingredients
- View dish details (price, description, ingredients)
- Recommend suitable dishes

Use available tools to fetch menu information.
Respond in Vietnamese, with a friendly and clear tone.
If a requested dish does not exist, suggest similar alternatives.
Only answer within menu and dish information scope.
"""


def create_menu_agent(llm: BaseChatModel):
    """Create the menu agent using ReAct pattern."""
    tools = [
        menu_tools.get_menu_categories,
        menu_tools.search_menu,
        menu_tools.get_dish_details,
        menu_tools.get_dishes_by_category,
    ]
    logger.info("FLOW menu_agent.init tool_count=%s", len(tools))
    agent = create_react_agent(llm, tools, prompt=MENU_AGENT_PROMPT)
    return agent


def create_menu_agent_node(llm: BaseChatModel):
    """Create the menu agent node for the graph."""
    from src.repositories.menu_repo import MenuRepository
    from src.tools.order_tools import _carts

    _menu_repo = MenuRepository()
    agent = create_menu_agent(llm)

    async def menu_agent_node(state: AgentState) -> dict:
        """Process menu-related queries.

        If the user clearly wants to add a dish to the cart:
        1. This node directly queries the DB to find the product.
        2. Adds it to the in-memory cart without relying on the LLM to call tools.
        3. Returns action=UPDATE_CART immediately.

        For pure information queries, the LLM handles it normally via ReAct.
        """
        session_id = state.get("session_id", "")
        logger.info("FLOW menu_agent.start session_id=%s", session_id)

        # Get original user message
        user_text = ""
        for msg in reversed(state.get("messages", [])):
            if getattr(msg, "type", "") == "human":
                user_text = msg.content
                break

        is_add_intent = _detect_add_intent(user_text)

        # ------------------------------------------------------------------
        # FAST PATH: Deterministic add-to-cart
        # Don't rely on LLM to call search + transfer tools. 
        # We query the DB directly and add to cart in code.
        # ------------------------------------------------------------------
        if is_add_intent:
            dish_query = _extract_dish_query(user_text)
            quantity = _extract_quantity(user_text)
            if not dish_query:
                dish_query = user_text  # fallback

            logger.info(
                "FLOW menu_agent.add_intent_detected session_id=%s dish_query=%s quantity=%s",
                session_id, dish_query, quantity,
            )

            try:
                product = await _menu_repo.get_product_by_id_or_name(dish_query)
            except Exception:
                logger.exception("FLOW menu_agent.db_lookup_failed session_id=%s", session_id)
                product = None

            if product:
                try:
                    image_url = await _menu_repo.get_product_image_url(product.id) or ""
                except Exception:
                    image_url = ""

                price = int(product.price)

                # Sync current_cart from App into _carts
                current_app_cart = list(state.get("current_cart") or [])
                _carts[session_id] = {
                    "items": current_app_cart,
                    "last_access": time.time(),
                }
                cart = _carts[session_id]["items"]

                # Merge: update quantity if same product already in cart
                found = False
                for item in cart:
                    if item.get("id") == str(product.id):
                        item["quantity"] += quantity
                        found = True
                        break
                if not found:
                    cart.append({
                        "id": str(product.id),
                        "name": product.name,
                        "price": price,
                        "quantity": quantity,
                        "url": image_url,
                    })

                logger.info(
                    "FLOW menu_agent.cart_updated session_id=%s product=%s quantity=%s cart_size=%s",
                    session_id, product.name, quantity, len(cart),
                )
                return {
                    "messages": [AIMessage(
                        content=f"Tôi đã thêm {quantity} {product.name} vào giỏ hàng cho bạn rồi nhé! 🛒",
                        name="menu_agent",
                    )],
                    "next_agent": "FINISH",
                    "last_topic": "action",
                    "action": "UPDATE_CART",
                    "action_data": list(cart),
                }
            else:
                # Dish not found: let LLM respond with a helpful error/suggestion
                logger.info(
                    "FLOW menu_agent.product_not_found session_id=%s query=%s",
                    session_id, dish_query,
                )
                # Fall through to LLM

        # ------------------------------------------------------------------
        # SLOW PATH: Pure information query — let LLM handle via ReAct
        # ------------------------------------------------------------------
        try:
            result = await agent.ainvoke({"messages": state["messages"]})
            last_message = result["messages"][-1]
            logger.info("FLOW menu_agent.done session_id=%s next_agent=FINISH", session_id)
            return {
                "messages": [AIMessage(content=last_message.content, name="menu_agent")],
                "next_agent": "FINISH",
                "last_topic": "menu",
            }
        except Exception:
            logger.error("FLOW menu_agent.failed session_id=%s", session_id, exc_info=True)
            return {
                "messages": [
                    AIMessage(
                        content="Xin lỗi, mình chưa thể xử lý yêu cầu thực đơn lúc này. Bạn vui lòng thử lại sau nhé.",
                        name="menu_agent",
                    )
                ],
                "next_agent": "FINISH",
                "last_topic": "menu",
            }

    return menu_agent_node
