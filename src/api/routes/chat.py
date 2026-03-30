"""Chat API routes."""

import uuid
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from src.api.schemas import ChatRequest, ChatResponse
from src.agents.graph import get_graph

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Chat"])


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
        session_id = request.session_id or str(uuid.uuid4())
        graph = get_graph()

        # Invoke the graph
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=request.message)],
                "session_id": session_id,
            }
        )

        # Get the last AI message
        messages = result.get("messages", [])
        response_text = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content and msg.type == "ai":
                response_text = msg.content
                break

        if not response_text:
            response_text = "Sorry, I couldn't process your request. Please try again."

        return ChatResponse(response=response_text, session_id=session_id)

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/chat/stream",
    summary="Chat with streaming response",
    description="Send a message and receive a streaming response via Server-Sent Events (SSE). "
    "Useful for displaying real-time responses in the app.",
)
async def chat_stream(request: ChatRequest):
    """Stream chat response using Server-Sent Events."""
    session_id = request.session_id or str(uuid.uuid4())

    async def event_generator():
        try:
            graph = get_graph()

            # Stream events from the graph
            async for event in graph.astream_events(
                {
                    "messages": [HumanMessage(content=request.message)],
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

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"event: error\ndata: {str(e)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
