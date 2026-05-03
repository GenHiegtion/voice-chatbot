"""Speech-to-text API routes."""

import uuid
import logging
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from src.api.schemas import SpeechToTextResponse, VoiceChatResponse
from src.api.sse import SSE_HEADERS, sse_event, stream_sse
from src.agents.graph import get_graph
from src.speech.asr import transcribe_audio
from src.speech.text_correction import correct_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Speech"])


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


@router.post(
    "/speech-to-text",
    response_model=SpeechToTextResponse,
    summary="Convert speech to text",
    description="Upload an audio file (WAV, MP3, OGG, FLAC) and receive transcribed Vietnamese text. "
    "The audio is processed through ASR model, then refined by LLM for spelling correction.",
)
async def speech_to_text(
    audio: UploadFile = File(...,
                             description="Audio file (WAV, MP3, OGG, FLAC)"),
):
    """Transcribe audio to Vietnamese text with LLM correction."""
    try:
        # Read audio bytes
        audio_bytes = await audio.read()
        logger.info(
            "FLOW speech_to_text.request_received upload_name=%s size_bytes=%s",
            audio.filename or "",
            len(audio_bytes),
        )

        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # Step 1: ASR transcription
        logger.info("FLOW speech_to_text.asr_start")
        original_text = await transcribe_audio(audio_bytes)
        logger.info("FLOW speech_to_text.asr_done text=%s", _preview_text(original_text))

        if not original_text:
            raise HTTPException(
                status_code=422, detail="Could not transcribe audio. Please try again.")

        # Step 2: LLM text correction
        logger.info("FLOW speech_to_text.correction_start")
        corrected_text = await correct_text(original_text)
        logger.info(
            "FLOW speech_to_text.correction_done corrected=%s",
            _preview_text(corrected_text),
        )

        return SpeechToTextResponse(
            original_text=original_text,
            corrected_text=corrected_text,
        )

    except HTTPException:
        raise
    except Exception:
        logger.error("FLOW speech_to_text.request_failed", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Speech-to-text failed")


@router.post(
    "/voice-chat",
    response_model=VoiceChatResponse,
    summary="Voice chat",
    description="Upload an audio file and the system will:\n"
    "1. Convert speech to text (ASR)\n"
    "2. Correct spelling errors (LLM)\n"
    "3. Process through AI chatbot\n"
    "4. Return the complete result",
)
async def voice_chat(
    audio: UploadFile = File(...,
                             description="Audio file (WAV, MP3, OGG, FLAC)"),
    session_id: str = Query(
        None, description="Session ID to continue an existing conversation"),
):
    """Full voice chat: audio → text → chatbot → response."""
    try:
        session_id = session_id or str(uuid.uuid4())

        # Read audio bytes
        audio_bytes = await audio.read()
        logger.info(
            "FLOW voice_chat.request_received session_id=%s upload_name=%s size_bytes=%s",
            session_id,
            audio.filename or "",
            len(audio_bytes),
        )

        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # Step 1: ASR transcription
        logger.info("FLOW voice_chat.asr_start session_id=%s", session_id)
        original_text = await transcribe_audio(audio_bytes)
        logger.info(
            "FLOW voice_chat.asr_done session_id=%s text=%s",
            session_id,
            _preview_text(original_text),
        )

        if not original_text:
            raise HTTPException(
                status_code=422, detail="Could not transcribe audio. Please try again.")

        # Step 2: LLM text correction
        logger.info("FLOW voice_chat.correction_start session_id=%s", session_id)
        corrected_text = await correct_text(original_text)
        logger.info(
            "FLOW voice_chat.correction_done session_id=%s corrected=%s",
            session_id,
            _preview_text(corrected_text),
        )

        # Step 3: Process through chatbot
        graph = get_graph()
        user_message = HumanMessage(content=corrected_text)
        logger.info("FLOW voice_chat.graph_invoke_start session_id=%s", session_id)
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
            "FLOW voice_chat.graph_invoke_done session_id=%s response=%s",
            session_id,
            _preview_text(response_text),
        )

        return VoiceChatResponse(
            original_text=original_text,
            corrected_text=corrected_text,
            response=response_text,
            session_id=session_id,
        )

    except HTTPException:
        raise
    except Exception:
        logger.error("FLOW voice_chat.request_failed session_id=%s", session_id or "", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Voice chat failed")


@router.post(
    "/voice-chat/stream",
    summary="Voice chat with streaming response",
    description="Upload an audio file and receive progress + chat response via Server-Sent Events (SSE).",
)
async def voice_chat_stream(
    request: Request,
    audio: UploadFile = File(..., description="Audio file (WAV, MP3, OGG, FLAC)"),
    session_id: str = Query(
        None, description="Session ID to continue an existing conversation"
    ),
):
    """Full voice chat with SSE: audio → text → chatbot → streamed response."""
    session_id = session_id or str(uuid.uuid4())
    request_id = str(uuid.uuid4())

    audio_bytes = await audio.read()
    logger.info(
        "FLOW voice_chat.stream_request_received session_id=%s upload_name=%s size_bytes=%s",
        session_id,
        audio.filename or "",
        len(audio_bytes),
    )

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    async def event_source():
        try:
            yield sse_event("meta", {"session_id": session_id, "request_id": request_id})

            yield sse_event("progress", {"stage": "asr", "status": "start"})
            original_text = await transcribe_audio(audio_bytes)
            if not original_text:
                yield sse_event(
                    "error",
                    {"message": "Could not transcribe audio. Please try again."},
                )
                yield sse_event("done", {"done": True})
                return
            yield sse_event("progress", {"stage": "asr", "status": "done"})

            yield sse_event("progress", {"stage": "correction", "status": "start"})
            corrected_text = await correct_text(original_text)
            yield sse_event("progress", {"stage": "correction", "status": "done"})

            yield sse_event("progress", {"stage": "chat", "status": "start"})
            graph = get_graph()
            user_message = HumanMessage(content=corrected_text)
            final_ai_message = ""
            streamed_chunks: list[str] = []
            action = "None"
            action_data = None
            STREAMING_NODES = {"menu_agent", "order_agent", "promotion_agent", "agent"}
            status_sent = set()

            async for event in graph.astream_events(
                {
                    "messages": [user_message],
                    "session_id": session_id,
                },
                version="v2",
            ):
                kind = event.get("event", "")
                node_name = event.get("metadata", {}).get("langgraph_node", "")

                if kind == "on_chain_start":
                    if node_name and node_name not in status_sent:
                        status_sent.add(node_name)
                        if node_name in STREAMING_NODES:
                            yield sse_event("status", {"stage": "answering", "node": node_name})
                        elif node_name in {"coordinator", "data_team", "action_team"}:
                            yield sse_event("status", {"stage": "routing", "node": node_name})

                if kind == "on_chat_model_stream" and node_name in STREAMING_NODES:
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        streamed_chunks.append(str(chunk.content))
                        yield sse_event("token", {"text": str(chunk.content)})

                if kind == "on_chain_end":
                    output = event.get("data", {}).get("output")
                    if isinstance(output, dict):
                        extracted = _extract_last_ai_message(output.get("messages", []))
                        if extracted:
                            final_ai_message = extracted
                        action = output.get("action", action) or action
                        action_data = output.get("action_data", action_data)

            yield sse_event("progress", {"stage": "chat", "status": "done"})

            response_text = final_ai_message or "".join(streamed_chunks).strip()
            if not response_text:
                response_text = "Sorry, I couldn't process your request. Please try again."

            yield sse_event(
                "final",
                {
                    "original_text": original_text,
                    "corrected_text": corrected_text,
                    "response": response_text,
                    "action": action or "None",
                    "action_data": action_data,
                    "session_id": session_id,
                },
            )
            yield sse_event("done", {"done": True})

        except Exception:
            logger.error(
                "FLOW voice_chat.stream_failed session_id=%s",
                session_id,
                exc_info=True,
            )
            yield sse_event("error", {"message": "Voice chat streaming failed"})
            yield sse_event("done", {"done": True})

    return StreamingResponse(
        stream_sse(request, event_source()),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
