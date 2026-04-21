"""Chat API routes."""

import uuid
import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from src.api.schemas import ChatRequest, ChatResponse
from src.api.session_history import append_session_turn, get_session_messages
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
    "and routes through coordinator -> team (data/action) -> specialized agent for processing.",
)
async def chat(request: ChatRequest):
    """Process a chat message through the multi-agent system."""
    try:
        user_text = request.message.strip()
        session_id = request.session_id or str(uuid.uuid4())
        graph = get_graph()
        user_message = HumanMessage(content=user_text)
        session_history = get_session_messages(session_id)
        graph_messages = session_history + [user_message]

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
            append_session_turn(session_id, user_text, response_text)
            return ChatResponse(response=response_text, session_id=session_id)

        logger.info(
            "FLOW chat.graph_invoke_start session_id=%s history_messages=%s",
            session_id,
            len(session_history),
        )

        # Invoke the graph
        result = await graph.ainvoke(
            {
                "messages": graph_messages,
                "session_id": session_id,
            }
        )

        response_text = _extract_last_ai_message(result.get("messages", []))

        if not response_text:
            response_text = "Sorry, I couldn't process your request. Please try again."

        append_session_turn(session_id, user_text, response_text)

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
            session_history = get_session_messages(session_id)
            graph_messages = session_history + [user_message]
            final_ai_message = ""
            streamed_chunks: list[str] = []

            logger.info(
                "FLOW chat.stream_graph_invoke_start session_id=%s history_messages=%s",
                session_id,
                len(session_history),
            )

            # Stream events from the graph
            async for event in graph.astream_events(
                {
                    "messages": graph_messages,
                    "session_id": session_id,
                },
                version="v2",
            ):
                kind = event.get("event", "")

                # Stream chat model tokens
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        streamed_chunks.append(str(chunk.content))
                        yield f"data: {chunk.content}\n\n"

                if kind == "on_chain_end":
                    output = event.get("data", {}).get("output")
                    if isinstance(output, dict):
                        extracted = _extract_last_ai_message(output.get("messages", []))
                        if extracted:
                            final_ai_message = extracted

            if final_ai_message:
                append_session_turn(session_id, request.message, final_ai_message)
                logger.info(
                    "FLOW chat.stream_history_saved session_id=%s response_chars=%s",
                    session_id,
                    len(final_ai_message),
                )
            elif streamed_chunks:
                fallback_response = "".join(streamed_chunks).strip()
                if fallback_response:
                    append_session_turn(session_id, request.message, fallback_response)
                    logger.info(
                        "FLOW chat.stream_history_saved_fallback session_id=%s response_chars=%s",
                        session_id,
                        len(fallback_response),
                    )

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
