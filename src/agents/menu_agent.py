"""Menu agent for handling menu-related queries."""

import logging

from langchain_core.messages import AIMessage
from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent

from src.agents.state import AgentState
from src.tools import menu_tools

logger = logging.getLogger(__name__)

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
