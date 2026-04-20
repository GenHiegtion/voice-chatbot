"""LLM-based text correction for ASR output."""

import logging
import time

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import get_correction_llm

logger = logging.getLogger(__name__)

CORRECTION_SYSTEM_PROMPT = """Bạn là một hệ thống chuyên chỉnh sửa văn bản tiếng Việt được tạo ra từ nhận dạng giọng nói (ASR/Speech-to-Text). Văn bản đầu vào thường chứa nhiều lỗi đặc trưng của ASR.

Nhiệm vụ của bạn:
1. Sửa lỗi chính tả và lỗi nhận diện giọng nói (ví dụ: "fở" → "phở", "côm" → "cơm")
2. Nhận diện và sửa tên riêng, từ nước ngoài bị phiên âm sai (ví dụ: "tíc tốc" → "TikTok", "gồ gồ" → "Google", "phây búc" → "Facebook", "rê an ma đríc" → "Real Madrid", "iu tu bơ" → "YouTube")
3. Sửa lỗi tách/ghép từ sai (ví dụ: "chátáp" → "chat", "su pe" → "super")
4. Thêm dấu câu phù hợp (dấu chấm, dấu phẩy, dấu hỏi) vào các vị trí tự nhiên trong câu
5. Viết hoa đúng đầu câu và tên riêng

Quy tắc quan trọng:
- KHÔNG thay đổi ý nghĩa hoặc nội dung của câu
- KHÔNG thêm hoặc bớt thông tin
- KHÔNG giải thích gì thêm
- Chỉ trả về văn bản đã sửa, không có gì khác

Ví dụ:
- Input: "tôi muốn đặc một tô fở bò"
- Output: "Tôi muốn đặt một tô phở bò."

- Input: "cho tôi xem mê nu đi có gà rán ken tắc ki không"
- Output: "Cho tôi xem menu đi, có gà rán KFC không?"

- Input: "ờ em không thích làm video đê ô ngắn và đấy là lý do mà em không làm tíc tốc"
- Output: "Ờ, em không thích làm video để ngắn, và đấy là lý do mà em không làm TikTok."
"""


def _is_expected_provider_error(exc: Exception) -> bool:
    """Identify transient upstream/provider errors to keep logs concise."""
    name = type(exc).__name__
    if name in {"ResponseError", "ConnectError", "ReadTimeout", "TimeoutException"}:
        return True

    text = str(exc).lower()
    return any(token in text for token in ["status code: 500", "internal server error", "timeout"])


async def correct_text(raw_text: str) -> str:
    """Correct ASR transcription errors using a lightweight LLM.

    Args:
        raw_text: Raw transcribed text from ASR model

    Returns:
        Corrected text
    """
    if not raw_text or not raw_text.strip():
        return raw_text

    llm = get_correction_llm()
    messages = [
        SystemMessage(content=CORRECTION_SYSTEM_PROMPT),
        HumanMessage(content=raw_text),
    ]

    last_error: Exception | None = None
    for attempt in range(1, 3):
        try:
            started_at = time.perf_counter()
            response = await llm.ainvoke(messages)
            corrected = response.content.strip()
            duration_ms = int((time.perf_counter() - started_at) * 1000)

            # Safety: if LLM returns empty or much longer than input, use original
            if not corrected or len(corrected) > len(raw_text) * 3:
                logger.warning("Correction LLM returned suspicious result; fallback to original")
                return raw_text

            logger.debug(
                "Text correction succeeded",
                extra={
                    "input_length": len(raw_text),
                    "output_length": len(corrected),
                    "duration_ms": duration_ms,
                },
            )
            return corrected
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                logger.info(
                    "Text correction provider failed; retrying once",
                    extra={"attempt": attempt},
                )
                continue

    if last_error is not None and _is_expected_provider_error(last_error):
        logger.info(
            "Text correction unavailable from provider; using original ASR text",
            extra={"error_type": type(last_error).__name__},
        )
    else:
        logger.error("Text correction failed unexpectedly; using original ASR text", exc_info=True)

    return raw_text
