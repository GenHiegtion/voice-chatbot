"""Shared helpers for Server-Sent Events (SSE)."""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import suppress
from typing import Any, AsyncIterable, AsyncIterator

from fastapi import Request

SSE_HEADERS = {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def sse_event(event: str, data: Any) -> str:
    """Format one SSE event with JSON payload."""
    payload = json.dumps(data, ensure_ascii=False)
    lines = payload.splitlines() or [""]
    parts: list[str] = []
    if event:
        parts.append(f"event: {event}")
    for line in lines:
        parts.append(f"data: {line}")
    return "\n".join(parts) + "\n\n"


async def stream_sse(
    request: Request,
    source: AsyncIterable[str],
    heartbeat_interval: int = 15,
) -> AsyncIterator[str]:
    """Stream SSE messages with periodic heartbeat."""
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    stop = asyncio.Event()

    async def pump() -> None:
        try:
            async for item in source:
                if stop.is_set():
                    break
                await queue.put(item)
                await asyncio.sleep(0)
        finally:
            await queue.put(None)

    task = asyncio.create_task(pump())
    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval)
            except asyncio.TimeoutError:
                yield sse_event("ping", {"ts": int(time.time())})
                continue
            if item is None:
                break
            yield item
    finally:
        stop.set()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
