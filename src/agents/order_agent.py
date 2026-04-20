"""Order agent for handling cart and order management."""

import logging

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent

from src.agents.state import AgentState
from src.tools.order_tools import add_to_cart, remove_from_cart, view_cart, update_cart_quantity, place_order

logger = logging.getLogger(__name__)

ORDER_AGENT_PROMPT = """Bạn là trợ lý quản lý đơn hàng nhà hàng. Nhiệm vụ của bạn là giúp khách hàng:

- Thêm món ăn vào giỏ hàng
- Xóa món khỏi giỏ hàng
- Cập nhật số lượng món
- Xem giỏ hàng hiện tại
- Xác nhận đặt hàng

Lưu ý quan trọng:
- Khi gọi các tools, bạn PHẢI truyền session_id từ state.
- Luôn xác nhận lại với khách trước khi đặt hàng chính thức.
- Trả lời bằng tiếng Việt, thân thiện và rõ ràng.
- Nếu khách muốn đặt hàng, hãy hỏi địa chỉ giao hàng nếu chưa có.
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
        session_msg = f"\n[Thông tin hệ thống: session_id của người dùng hiện tại là '{session_id}'. Hãy sử dụng session_id này khi gọi các order tools.]"

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
