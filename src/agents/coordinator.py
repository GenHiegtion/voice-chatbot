"""Coordinator (Supervisor) agent that routes user messages to specialized agents."""

import asyncio
import json
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage

from src.agents.state import AgentState

logger = logging.getLogger(__name__)


def _is_expected_provider_error(exc: Exception) -> bool:
    """Identify transient upstream/provider errors to keep logs concise."""
    name = type(exc).__name__
    if name in {"ResponseError", "ConnectError", "ReadTimeout", "TimeoutException"}:
        return True

    text = str(exc).lower()
    return any(token in text for token in ["status code: 500", "internal server error", "timeout"])

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

        session_id = state.get("session_id", "")
        user_preview = ""
        for msg in reversed(state["messages"]):
            if getattr(msg, "type", "") == "human" and getattr(msg, "content", ""):
                user_preview = " ".join(str(msg.content).split())[:160]
                break

        logger.info(
            "FLOW coordinator.start session_id=%s message=%s",
            session_id,
            user_preview,
        )

        response = None
        for attempt in range(1, 3):
            try:
                response = await llm.ainvoke(messages)
                break
            except Exception as exc:
                logger.warning(
                    "FLOW coordinator.llm_failed session_id=%s attempt=%s",
                    session_id,
                    attempt,
                )
                # Log traceback only for unexpected exceptions.
                if not _is_expected_provider_error(exc):
                    logger.debug(
                        "FLOW coordinator.llm_failed_details session_id=%s attempt=%s",
                        session_id,
                        attempt,
                        exc_info=True,
                    )
                if attempt < 2:
                    await asyncio.sleep(0.4 * attempt)

        if response is None:
            fallback = (
                "Xin lỗi, hệ thống AI đang tạm bận. Bạn vui lòng thử lại sau ít phút nhé."
            )
            logger.error("FLOW coordinator.fallback session_id=%s", session_id)
            return {
                "next_agent": "FINISH",
                "messages": [AIMessage(content=fallback)],
            }

        content = response.content

        # Parse the routing decision
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

        logger.info(
            "FLOW coordinator.route_decision session_id=%s next_agent=%s",
            session_id,
            next_agent,
        )

        # If FINISH, add the coordinator's response as a message
        if next_agent == "FINISH" and direct_response:
            result["messages"] = [AIMessage(content=direct_response)]

        return result

    return coordinator_node
