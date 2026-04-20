"""Chat API routes."""

import uuid
import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from src.api.schemas import ChatRequest, ChatResponse
from src.agents.graph import get_graph

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Chat"])

_GREETING_PATTERN = re.compile(r"^(hello|hi|hey|xin chao|xin chào|chao|chào)\W*$", re.IGNORECASE)


def _extract_last_ai_message(messages: list[Any]) -> str:
    """Extract the latest AI message content from graph output messages."""
    for msg in reversed(messages):
        if getattr(msg, "type", "") == "ai" and getattr(msg, "content", ""):
            return msg.content
    return ""


def _preview_text(text: str, limit: int = 160) -> str:
    """Return a single-line safe preview for logs."""
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."


def _is_simple_greeting(text: str) -> bool:
    """Detect short greeting messages that can be answered without LLM call."""
    return bool(_GREETING_PATTERN.match(text.strip()))


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a chat message",
    description="Send a text message to the AI chatbot. The system automatically analyzes user intent "
    "and routes to the appropriate agent (menu, order, promotion) for processing.",
)
async def chat(request: ChatRequest):
    """Process a chat message through the multi-agent system."""
    try:
        user_text = request.message.strip()
        session_id = request.session_id or str(uuid.uuid4())
        graph = get_graph()
        user_message = HumanMessage(content=user_text)

        logger.info(
            "FLOW chat.request_received session_id=%s message=%s",
            session_id,
            _preview_text(user_text),
        )

        if _is_simple_greeting(user_text):
            response_text = "Xin chào! Mình có thể giúp bạn xem menu, thêm món vào giỏ, kiểm tra khuyến mãi hoặc đặt hàng."
            logger.info(
                "FLOW chat.shortcut_greeting session_id=%s response=%s",
                session_id,
                _preview_text(response_text),
            )
            return ChatResponse(response=response_text, session_id=session_id)

        logger.info("FLOW chat.graph_invoke_start session_id=%s", session_id)

        # Invoke the graph
        result = await graph.ainvoke(
            {
                "messages": [user_message],
                "session_id": session_id,
            }
        )

        response_text = _extract_last_ai_message(result.get("messages", []))

        if not response_text:
            response_text = "Sorry, I couldn't process your request. Please try again."

        logger.info(
            "FLOW chat.graph_invoke_done session_id=%s next_agent=%s response=%s",
            session_id,
            result.get("next_agent", ""),
            _preview_text(response_text),
        )

        return ChatResponse(response=response_text, session_id=session_id)

    except Exception:
        logger.error(
            "FLOW chat.request_failed session_id=%s message=%s",
            request.session_id or "",
            _preview_text(request.message),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Internal server error")


@router.post(
    "/chat/stream",
    summary="Chat with streaming response",
    description="Send a message and receive a streaming response via Server-Sent Events (SSE). "
    "Useful for displaying real-time responses in the app.",
)
async def chat_stream(request: ChatRequest):
    """Stream chat response using Server-Sent Events."""
    session_id = request.session_id or str(uuid.uuid4())
    logger.info(
        "FLOW chat.stream_request_received session_id=%s message=%s",
        session_id,
        _preview_text(request.message),
    )

    async def event_generator():
        try:
            graph = get_graph()
            user_message = HumanMessage(content=request.message)

            # Stream events from the graph
            async for event in graph.astream_events(
                {
                    "messages": [user_message],
                    "session_id": session_id,
                },
                version="v2",
            ):
                kind = event.get("event", "")

                # Stream chat model tokens
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield f"data: {chunk.content}\n\n"

            # Send session_id and end signal
            yield f"event: session_id\ndata: {session_id}\n\n"
            yield "event: done\ndata: [DONE]\n\n"

        except Exception:
            logger.error("FLOW chat.stream_failed session_id=%s", session_id, exc_info=True)
            yield "event: error\ndata: Streaming failed\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
