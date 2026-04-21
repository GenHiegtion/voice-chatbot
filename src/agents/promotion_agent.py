"""Promotion agent for handling discount and promotion queries."""

import logging

from langchain_core.messages import AIMessage
from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent

from src.agents.state import AgentState
from src.tools import promo_tools

logger = logging.getLogger(__name__)

PROMOTION_AGENT_PROMPT = """You are the promotions and discounts specialist assistant. Your responsibilities are to help users:

- View active promotions
- Check promotions for specific dishes
- Suggest ways to save money when ordering
- Suggest best currently active deals

Use available tools to retrieve promotion information.
Respond in Vietnamese, with a warm and clear tone.
Only provide deals tied to currently selling dishes.
"""


def create_promotion_agent(llm: BaseChatModel):
    """Create the promotion agent using ReAct pattern."""
    tools = [
        promo_tools.get_active_promotions,
        promo_tools.check_promotion_for_dish,
        promo_tools.get_best_deals,
    ]
    logger.info("FLOW promotion_agent.init tool_count=%s", len(tools))
    agent = create_react_agent(llm, tools, prompt=PROMOTION_AGENT_PROMPT)
    return agent


def create_promotion_agent_node(llm: BaseChatModel):
    """Create the promotion agent node for the graph."""
    agent = create_promotion_agent(llm)

    async def promotion_agent_node(state: AgentState) -> dict:
        """Process promotion-related queries."""
        session_id = state.get("session_id", "")
        logger.info("FLOW promotion_agent.start session_id=%s", session_id)
        try:
            result = await agent.ainvoke({"messages": state["messages"]})
            last_message = result["messages"][-1]
            logger.info("FLOW promotion_agent.done session_id=%s", session_id)
            return {
                "messages": [AIMessage(content=last_message.content, name="promotion_agent")],
                "next_agent": "FINISH",
                "last_topic": "promotion",
            }
        except Exception:
            logger.error("FLOW promotion_agent.failed session_id=%s", session_id, exc_info=True)
            return {
                "messages": [
                    AIMessage(
                        content="Xin lỗi, mình chưa thể kiểm tra khuyến mãi lúc này. Bạn vui lòng thử lại sau nhé.",
                        name="promotion_agent",
                    )
                ],
                "next_agent": "FINISH",
                "last_topic": "promotion",
            }

    return promotion_agent_node
