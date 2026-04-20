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
- When using tools, you MUST pass the session_id from state.
- Always confirm with the customer before placing the final order.
- Respond in Vietnamese, clearly and politely.
- Ask for delivery address if the user wants to place an order and the address is missing.
"""


def create_order_agent(llm: BaseChatModel):
    """Create the order agent using ReAct pattern."""
    tools = [add_to_cart, remove_from_cart,
             view_cart, update_cart_quantity, place_order]
    agent = create_react_agent(llm, tools, prompt=ORDER_AGENT_PROMPT)
    return agent


def create_order_agent_node(llm: BaseChatModel):
    """Create the order agent node for the graph."""
    agent = create_order_agent(llm)

    async def order_agent_node(state: AgentState) -> dict:
        """Process order-related actions."""
        # Inject session_id into the message context so the agent knows which cart to use
        session_id = state.get("session_id", "default")
        logger.info("FLOW order_agent.start session_id=%s", session_id)
        session_msg = (
            f"\n[System context: the current user's session_id is '{session_id}'. "
            "Use this session_id whenever calling order tools.]"
        )

        messages = list(state["messages"])
        # Add session context to the last user message
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                augmented = HumanMessage(
                    content=last_msg.content + session_msg)
                messages = messages[:-1] + [augmented]

        try:
            result = await agent.ainvoke({"messages": messages})
            last_message = result["messages"][-1]
            logger.info("FLOW order_agent.done session_id=%s", session_id)
            return {
                "messages": [AIMessage(content=last_message.content, name="order_agent")],
                "next_agent": "FINISH",
            }
        except Exception:
            logger.error("FLOW order_agent.failed session_id=%s", session_id, exc_info=True)
            return {
                "messages": [
                    AIMessage(
                        content="Xin lỗi, mình chưa thể xử lý thao tác đơn hàng lúc này. Bạn vui lòng thử lại sau nhé.",
                        name="order_agent",
                    )
                ],
                "next_agent": "FINISH",
            }

    return order_agent_node
