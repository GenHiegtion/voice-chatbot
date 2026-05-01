"""Run the MCP server as a standalone process."""

from __future__ import annotations

import logging
import os
import sys

import uvicorn

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.config import get_settings
from src.mcp.server import create_mcp_app


def _configure_logging(log_level: str) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )


def main() -> int:
    settings = get_settings()
    _configure_logging(settings.mcp_log_level)

    if not settings.mcp_enabled:
        logging.error("MCP server is disabled. Set MCP_ENABLED=true to run.")
        return 1

    app = create_mcp_app()
    uvicorn.run(
        app,
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level=settings.mcp_log_level.lower(),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
