"""Speech-to-text API routes."""

import uuid
import logging

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from langchain_core.messages import HumanMessage

from src.api.schemas import SpeechToTextResponse, VoiceChatResponse
from src.agents.graph import get_graph
from src.speech.asr import transcribe_audio
from src.speech.text_correction import correct_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Speech"])


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

        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # Step 1: ASR transcription
        original_text = await transcribe_audio(audio_bytes)

        if not original_text:
            raise HTTPException(
                status_code=422, detail="Could not transcribe audio. Please try again.")

        # Step 2: LLM text correction
        corrected_text = await correct_text(original_text)

        return SpeechToTextResponse(
            original_text=original_text,
            corrected_text=corrected_text,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Speech-to-text error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Speech-to-text failed: {str(e)}")


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

        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # Step 1: ASR transcription
        original_text = await transcribe_audio(audio_bytes)

        if not original_text:
            raise HTTPException(
                status_code=422, detail="Could not transcribe audio. Please try again.")

        # Step 2: LLM text correction
        corrected_text = await correct_text(original_text)

        # Step 3: Process through chatbot
        graph = get_graph()
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=corrected_text)],
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

        return VoiceChatResponse(
            original_text=original_text,
            corrected_text=corrected_text,
            response=response_text,
            session_id=session_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Voice chat failed: {str(e)}")
