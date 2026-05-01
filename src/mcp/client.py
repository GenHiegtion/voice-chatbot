"""MCP client helper for tool calls."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent

from src.config import get_settings

logger = logging.getLogger(__name__)


def _mcp_url() -> str:
    settings = get_settings()
    host = settings.mcp_host
    port = settings.mcp_port
    return f"http://{host}:{port}/mcp"


def _auth_headers() -> dict[str, str]:
    token = get_settings().mcp_auth_token
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _extract_text(contents: list[Any]) -> str:
    for item in contents:
        if isinstance(item, TextContent):
            return item.text
    return ""


async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Call MCP tool over streamable HTTP and return text output."""
    settings = get_settings()
    if not settings.mcp_auth_token:
        return "MCP_AUTH_TOKEN is missing."

    url = _mcp_url()
    headers = _auth_headers()
    try:
        async with httpx.AsyncClient(headers=headers) as http_client:
            async with streamable_http_client(url, http_client=http_client) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=arguments)
    except Exception:
        logger.exception("MCP tool call failed tool=%s", tool_name)
        return "MCP tool call failed."

    if result.isError:
        text = _extract_text(result.content)
        return text or "MCP tool error."

    if result.content:
        text = _extract_text(result.content)
        if text:
            return text

    if result.structuredContent is not None:
        return json.dumps(result.structuredContent)

    return ""
