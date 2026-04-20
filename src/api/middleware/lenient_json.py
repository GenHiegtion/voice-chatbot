"""Middleware to tolerate common JSON formatting mistakes in request bodies."""

import json
import logging
import re
from typing import Optional

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

# Matches a trailing comma before a closing object/array token.
_TRAILING_COMMA_PATTERN = re.compile(r",(?=\s*[}\]])")


def _normalize_json_bytes(body: bytes) -> Optional[bytes]:
    """Try to normalize common malformed JSON payloads.

    Supported fixes:
    - Trailing commas before `}` or `]`
    - JSON object accidentally wrapped in a JSON string

    Returns normalized bytes if a safe fix is possible, else None.
    """
    if not body:
        return None

    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return None

    stripped = text.strip()
    if not stripped:
        return None

    # If already valid JSON object/array, keep original body.
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, (dict, list)):
            return None
        if isinstance(parsed, str):
            stripped = parsed.strip()
        else:
            return None
    except json.JSONDecodeError:
        pass

    # Remove trailing commas and try parsing again.
    candidate = _TRAILING_COMMA_PATTERN.sub("", stripped)
    try:
        reparsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    # Handle nested JSON string again after first normalization pass.
    if isinstance(reparsed, str):
        try:
            reparsed = json.loads(reparsed)
        except json.JSONDecodeError:
            return None

    if not isinstance(reparsed, (dict, list)):
        return None

    normalized = json.dumps(reparsed, ensure_ascii=False).encode("utf-8")
    if normalized == body:
        return None
    return normalized


class LenientJSONMiddleware:
    """Normalize malformed JSON payloads before FastAPI body parsing."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method", "")).upper()
        if method not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        content_type = headers.get("content-type", "")
        if "application/json" not in content_type:
            await self.app(scope, receive, send)
            return

        body_chunks: list[bytes] = []
        while True:
            message: Message = await receive()
            if message["type"] != "http.request":
                continue

            body_chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break

        raw_body = b"".join(body_chunks)
        normalized = _normalize_json_bytes(raw_body)
        if normalized is not None:
            logger.debug("Normalized malformed JSON request body")
            raw_body = normalized

        sent_once = False

        async def receive_once() -> Message:
            nonlocal sent_once
            if sent_once:
                return {"type": "http.request", "body": b"", "more_body": False}
            sent_once = True
            return {"type": "http.request", "body": raw_body, "more_body": False}

        await self.app(scope, receive_once, send)
