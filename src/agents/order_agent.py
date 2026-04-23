"""Order agent for handling cart and order management."""

import logging

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent

from src.agents.state import AgentState
from src.tools.order_tools import add_to_cart, remove_from_cart, view_cart, update_cart_quantity, place_order

logger = logging.getLogger(__name__)

ORDER_AGENT_PROMPT = """You are the restaurant ordering assistant. Your responsibilities are to help users:

- Add items to the cart
- Remove items from the cart
- Update item quantities
- View the current cart
- Confirm and place orders

Important notes:
- You MUST ACTUALLY CALL the order tools (e.g., add_to_cart, remove_from_cart) to perform actions. NEVER just output text saying you did it without calling the tool!
- When using tools, you MUST pass the session_id from state.
- Always confirm with the customer before placing the final order.
- Respond in Vietnamese, clearly and politely.
- Ask for delivery address if the user wants to place an order and the address is missing.
"""


def create_order_agent(llm: BaseChatModel):
    """Create the ReAct order agent."""
    tools = [add_to_cart, remove_from_cart, view_cart, update_cart_quantity, place_order]
    agent = create_react_agent(llm, tools, prompt=ORDER_AGENT_PROMPT)
    return agent


def create_order_agent_node(llm: BaseChatModel):
    """Create the order agent node for the graph."""
    react_agent = create_order_agent(llm)

    async def order_agent_node(state: AgentState) -> dict:
        """Process order-related queries via ReAct."""
        session_id = state.get("session_id", "default")
        logger.info("FLOW order_agent.react_start session_id=%s", session_id)
        
        session_msg = (
            f"\n[System context: the current user's session_id is '{session_id}'. "
            "Use this session_id whenever calling order tools.]"
        )

        messages = list(state["messages"])
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                augmented = HumanMessage(content=last_msg.content + session_msg)
                messages = messages[:-1] + [augmented]

        # Sync current_cart from state to order_tools in-memory _carts
        from src.tools.order_tools import _carts
        import time
        
        current_app_cart = list(state.get("current_cart") or [])
        # Always sync with the app's current_cart as the source of truth for this request
        _carts[session_id] = {"items": current_app_cart, "last_access": time.time()}

        # Call the ReAct agent to use tools
        try:
            result = await react_agent.ainvoke({"messages": messages})
            last_message = result["messages"][-1]
            
            # Post-process: extract the current cart state from tools to send to App
            from src.tools.order_tools import _carts
            cart_items = _carts.get(session_id, {}).get("items", [])
            
            # If the user performed an action that leaves items in the cart, trigger UPDATE_CART
            action = "UPDATE_CART" if cart_items else "None"
            action_data = cart_items if cart_items else None
            
            logger.info("FLOW order_agent.react_done session_id=%s cart_size=%s", session_id, len(cart_items))
            return {
                "messages": [AIMessage(content=last_message.content, name="order_agent")],
                "action": action,
                "action_data": action_data,
                "next_agent": "FINISH",
                "last_topic": "action",
            }
            
        except Exception:
            logger.error("FLOW order_agent.react_failed session_id=%s", session_id, exc_info=True)
            return {
                "messages": [
                    AIMessage(
                        content="Xin lỗi, mình chưa thể xử lý thao tác đơn hàng lúc này. Bạn vui lòng thử lại sau nhé.",
                        name="order_agent",
                    )
                ],
                "action": "None",
                "action_data": None,
                "next_agent": "FINISH",
                "last_topic": "action",
            }

    return order_agent_node
