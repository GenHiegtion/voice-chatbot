from typing import Optional

from pydantic import BaseModel, Field


# ===== Chat =====
class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str = Field(..., description="User message text")
    session_id: Optional[str] = Field(
        None, description="Session ID to continue a conversation. If not provided, a new session is created."
    )


class ChatResponse(BaseModel):
    """Response body for chat endpoint."""

    response: str = Field(..., description="AI assistant response")
    session_id: str = Field(...,
                            description="Session ID for conversation continuity")


# ===== Speech-to-Text =====
class SpeechToTextResponse(BaseModel):
    """Response body for speech-to-text endpoint."""

    original_text: str = Field(...,
                               description="Raw transcription from ASR model")
    corrected_text: str = Field(..., description="Text after LLM correction")


# ===== Voice Chat =====
class VoiceChatResponse(BaseModel):
    """Response body for voice chat endpoint (speech-to-text + chatbot)."""

    original_text: str = Field(...,
                               description="Raw transcription from ASR model")
    corrected_text: str = Field(..., description="Text after LLM correction")
    response: str = Field(..., description="AI assistant response")
    session_id: str = Field(...,
                            description="Session ID for conversation continuity")
