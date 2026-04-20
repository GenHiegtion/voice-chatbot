"""Speech-to-text API routes."""

import uuid
import logging
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from langchain_core.messages import HumanMessage

from src.api.schemas import SpeechToTextResponse, VoiceChatResponse
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
