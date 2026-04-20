"""Promotion agent for handling discount and promotion queries."""

import logging

from langchain_core.messages import AIMessage
from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent

from src.agents.state import AgentState
from src.tools.promotion_tools import get_active_promotions, check_promotion_for_dish, check_coupon

logger = logging.getLogger(__name__)

PROMOTION_AGENT_PROMPT = """You are the promotions and discounts specialist assistant. Your responsibilities are to help users:

- View active promotions
- Check promotions for specific dishes
- Validate coupon codes
- Suggest ways to save money when ordering

Use available tools to retrieve promotion information.
Respond in Vietnamese, with a warm and clear tone.
Proactively suggest suitable combos or discounts.
"""


def create_promotion_agent(llm: BaseChatModel):
    """Create the promotion agent using ReAct pattern."""
    tools = [get_active_promotions, check_promotion_for_dish, check_coupon]
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
            }

    return promotion_agent_node
