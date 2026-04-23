from typing import Any, Optional

from pydantic import BaseModel, Field


# ===== Chat =====
class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str = Field(..., description="User message text")
    session_id: Optional[str] = Field(
        None, description="Session ID to continue a conversation. If not provided, a new session is created."
    )
    current_cart: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Current cart items from the App. Each item: "
            '{"id": str, "name": str, "price": int, "quantity": int, "image": str}. '
            "Empty list if cart is empty."
        ),
    )


class ChatResponse(BaseModel):
    """Response body for chat endpoint."""

    response: str = Field(..., description="AI assistant response")
    session_id: str = Field(...,
                            description="Session ID for conversation continuity")
    action: str = Field(
        default="None",
        description="Cart action directive. 'UPDATE_CART' when items should be added to cart; 'None' otherwise.",
    )
    action_data: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description=(
            "Cart items when action='UPDATE_CART'. "
            'Each item: {"id": str, "name": str, "price": int, "quantity": int, "image": str}. '
            "null when action is None."
        ),
    )


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
