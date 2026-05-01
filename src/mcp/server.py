"""MCP server setup and ASGI app factory."""

from __future__ import annotations

import contextlib
import logging
from typing import Callable

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from src.config import get_settings
from src.mcp.tools import menu as menu_mcp
from src.mcp.tools import order as order_mcp
from src.mcp.tools import promotion as promo_mcp

logger = logging.getLogger(__name__)


class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Simple bearer token auth for MCP endpoints."""

    def __init__(self, app: Callable, token: str) -> None:
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        auth_header = request.headers.get("authorization", "")
        expected = f"Bearer {self._token}"
        if auth_header != expected:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)


def _normalize_transport(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized == "http":
        return "streamable-http"
    return normalized


def _validate_settings() -> str:
    settings = get_settings()
    if not settings.mcp_auth_token:
        raise RuntimeError("MCP_AUTH_TOKEN is required")

    transport = _normalize_transport(settings.mcp_transport)
    if transport != "streamable-http":
        raise RuntimeError("Only streamable-http transport is supported")
    return transport


def create_mcp_server() -> FastMCP:
    """Create the FastMCP server and register tool adapters."""
    _validate_settings()

    mcp = FastMCP(
        name="Voice Chatbot MCP",
        instructions="Expose menu, promotion, and order tools.",
        stateless_http=True,
        json_response=True,
    )

    mcp.tool()(menu_mcp.menu_get_menu_categories)
    mcp.tool()(menu_mcp.menu_search_menu)
    mcp.tool()(menu_mcp.menu_get_dish_details)
    mcp.tool()(menu_mcp.menu_get_dishes_by_category)
    mcp.tool()(menu_mcp.menu_get_best_selling_products)

    mcp.tool()(promo_mcp.promotion_get_active_promotions)
    mcp.tool()(promo_mcp.promotion_check_promotion_for_dish)
    mcp.tool()(promo_mcp.promotion_get_best_deals)

    mcp.tool()(order_mcp.order_add_to_cart)
    mcp.tool()(order_mcp.order_remove_from_cart)
    mcp.tool()(order_mcp.order_view_cart)
    mcp.tool()(order_mcp.order_update_cart_quantity)
    mcp.tool()(order_mcp.order_place_order)

    return mcp


async def _healthcheck(_request: Request) -> Response:
    return JSONResponse({"status": "ok"})


def create_mcp_app() -> Starlette:
    """Create the ASGI app that serves the MCP server."""
    settings = get_settings()
    mcp = create_mcp_server()

    mcp_app = mcp.streamable_http_app()
    mcp_app = TokenAuthMiddleware(mcp_app, settings.mcp_auth_token)

    @contextlib.asynccontextmanager
    async def lifespan(_app: Starlette):
        async with mcp.session_manager.run():
            yield

    return Starlette(
        routes=[
            Route("/health", _healthcheck, methods=["GET"]),
            Mount("/", app=mcp_app),
        ],
        lifespan=lifespan,
    )
