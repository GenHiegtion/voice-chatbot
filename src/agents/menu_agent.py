"""Menu agent for handling menu-related queries."""

import logging

from langchain_core.messages import AIMessage
from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent

from src.agents.state import AgentState
from src.tools.menu_tools import get_menu_categories, search_menu, get_dish_details, get_dishes_by_category

logger = logging.getLogger(__name__)

MENU_AGENT_PROMPT = """Bạn là trợ lý chuyên về thực đơn nhà hàng. Nhiệm vụ của bạn là giúp khách hàng:

- Xem danh mục thực đơn
- Tìm kiếm món ăn theo tên hoặc nguyên liệu
- Xem chi tiết món ăn (giá, mô tả, nguyên liệu)
- Gợi ý món ăn phù hợp

Sử dụng các tools có sẵn để tra cứu thông tin thực đơn. Luôn trả lời bằng tiếng Việt, thân thiện và chi tiết.
Nếu khách hỏi món không có trong menu, hãy gợi ý các món tương tự.
"""


def create_menu_agent(llm: BaseChatModel):
    """Create the menu agent using ReAct pattern."""
    tools = [get_menu_categories, search_menu,
             get_dish_details, get_dishes_by_category]
    agent = create_react_agent(llm, tools, prompt=MENU_AGENT_PROMPT)
    return agent


def create_menu_agent_node(llm: BaseChatModel):
    """Create the menu agent node for the graph."""
    agent = create_menu_agent(llm)

    async def menu_agent_node(state: AgentState) -> dict:
        """Process menu-related queries."""
        session_id = state.get("session_id", "")
        logger.info("FLOW menu_agent.start session_id=%s", session_id)
        try:
            result = await agent.ainvoke({"messages": state["messages"]})
            # Get the last AI message from the agent
            last_message = result["messages"][-1]
            logger.info("FLOW menu_agent.done session_id=%s", session_id)
            return {
                "messages": [AIMessage(content=last_message.content, name="menu_agent")],
                "next_agent": "FINISH",
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
            }

    return menu_agent_node
