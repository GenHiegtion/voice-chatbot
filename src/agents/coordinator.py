"""Coordinator (Supervisor) agent that routes user messages to specialized agents."""

from langchain_core.messages import SystemMessage
from langchain_core.language_models import BaseChatModel

from src.agents.state import AgentState

COORDINATOR_SYSTEM_PROMPT = """Bạn là trợ lý AI điều phối cho ứng dụng đặt món ăn. Nhiệm vụ của bạn là:

1. Phân tích tin nhắn của người dùng
2. Quyết định chuyển đến agent chuyên biệt phù hợp hoặc trả lời trực tiếp

Các agent chuyên biệt có sẵn:
- **menu_agent**: Xử lý câu hỏi về thực đơn, tìm kiếm món ăn, xem chi tiết món, duyệt danh mục
- **order_agent**: Quản lý giỏ hàng (thêm/xóa/sửa món), xem giỏ hàng, đặt hàng
- **promotion_agent**: Thông tin khuyến mãi, giảm giá, mã coupon

Quy tắc:
- Nếu người dùng hỏi về thực đơn, món ăn, nguyên liệu, giá cả → route đến menu_agent
- Nếu người dùng muốn thêm/xóa/sửa món trong giỏ, xem giỏ hàng, đặt hàng → route đến order_agent
- Nếu người dùng hỏi về khuyến mãi, giảm giá, mã coupon → route đến promotion_agent
- Nếu là câu hỏi chung (chào hỏi, cảm ơn, hỏi thông tin chung) → trả lời trực tiếp (FINISH)

Hãy luôn thân thiện, lịch sự và hữu ích. Trả lời bằng tiếng Việt.

QUAN TRỌNG: Bạn PHẢI trả lời bằng JSON với format:
{{"next": "<agent_name hoặc FINISH>", "response": "<câu trả lời nếu FINISH, hoặc rỗng nếu route>"}}
"""


def create_coordinator_node(llm: BaseChatModel):
    """Create the coordinator node function."""

    async def coordinator_node(state: AgentState) -> dict:
        """Coordinator agent that analyzes intent and routes to sub-agents."""
        messages = [SystemMessage(
            content=COORDINATOR_SYSTEM_PROMPT)] + state["messages"]

        response = await llm.ainvoke(messages)
        content = response.content

        # Parse the routing decision
        import json

        try:
            # Try to extract JSON from the response
            # Handle cases where LLM wraps JSON in markdown code blocks
            cleaned = content
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]

            decision = json.loads(cleaned.strip())
            next_agent = decision.get("next", "FINISH")
            direct_response = decision.get("response", "")
        except (json.JSONDecodeError, IndexError):
            # If parsing fails, treat as direct response
            next_agent = "FINISH"
            direct_response = content

        # Validate next_agent
        valid_agents = {"menu_agent", "order_agent",
                        "promotion_agent", "FINISH"}
        if next_agent not in valid_agents:
            next_agent = "FINISH"

        result = {"next_agent": next_agent}

        # If FINISH, add the coordinator's response as a message
        if next_agent == "FINISH" and direct_response:
            from langchain_core.messages import AIMessage

            result["messages"] = [AIMessage(content=direct_response)]

        return result

    return coordinator_node
