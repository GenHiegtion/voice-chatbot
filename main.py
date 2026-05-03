"""Voice Chatbot - FastAPI Application

AI Service for a food ordering app, including:
- Multi-Agent Chatbot (LangGraph) with Coordinator, Menu, Order, Promotion agents
- Vietnamese Speech-to-Text (ChunkFormer ASR)
- LLM post-processing text correction
"""

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.lenient_json import LenientJSONMiddleware
from src.api.routes import chat, speech
from src.config import configure_model_cache_environment, get_settings

# Global reference to the MCP server subprocess (used when TOOL_PROVIDER=mcp)
_mcp_process: asyncio.subprocess.Process | None = None


class _CheckpointLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if (
            "missing tensor:" in msg
            or "unexpected tensor:" in msg
            or "Checkpoint: loading from checkpoint" in msg
        ):
            return False
        return True


def _configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )

    # Suppress noisy third-party logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chunkformer").setLevel(logging.WARNING)

    checkpoint_filter = _CheckpointLogFilter()
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(checkpoint_filter)

_configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Voice Chatbot",
    description=(
        "AI Service for a food ordering application.\n\n"
        "## Features\n"
        "- 🤖 **AI Chatbot**: Multi-agent system for ordering, browsing menus, promotions\n"
        "- 🎤 **Speech-to-Text**: Convert Vietnamese speech to text\n"
        "- 🗣️ **Voice Chat**: Combine speech recognition + chatbot\n\n"
        "## Agents\n"
        "- **Coordinator**: Intent analysis & routing\n"
        "- **Menu Agent**: Browse menu, search dishes\n"
        "- **Order Agent**: Cart management, checkout\n"
        "- **Promotion Agent**: Promotions, coupons, deals\n"
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tolerate common JSON formatting mistakes from clients.
app.add_middleware(LenientJSONMiddleware)

# Include routers
app.include_router(chat.router)
app.include_router(speech.router)


async def _start_mcp_subprocess(settings) -> asyncio.subprocess.Process | None:
    """Start the MCP server as a background subprocess.

    The function launches ``scripts/run_mcp_server.py`` using the same Python
    interpreter (via ``uv run``) and waits up to 15 s for the server to become
    reachable before returning, so that the first tool call does not race with
    server startup.
    """
    cmd = ["uv", "run", "python", "scripts/run_mcp_server.py"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        logger.info("MCP subprocess started pid=%s cmd=%s", proc.pid, " ".join(cmd))
    except Exception:
        logger.warning("Failed to start MCP subprocess", exc_info=True)
        return None

    # Wait until the MCP server's HTTP port is reachable (max 15 s)
    host = settings.mcp_client_host
    port = settings.mcp_port
    deadline = asyncio.get_event_loop().time() + 15
    while asyncio.get_event_loop().time() < deadline:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            logger.info("MCP server is ready host=%s port=%s", host, port)
            return proc
        except OSError:
            await asyncio.sleep(0.3)

    logger.warning(
        "MCP server did not become ready within 15 s host=%s port=%s — "
        "tool calls via MCP may fail until it starts",
        host, port,
    )
    return proc


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize app-level resources once per process startup."""
    global _mcp_process

    settings = get_settings()
    configure_model_cache_environment()

    from src.agents.graph import get_graph
    from src.database import probe_database_connection

    # Build graph early to avoid first-request latency.
    get_graph()
    logger.info("Graph initialized")

    db_ready = await probe_database_connection()
    logger.info("Database probe status=%s", "ready" if db_ready else "unavailable")

    # Auto-start the MCP server subprocess when TOOL_PROVIDER=mcp
    if settings.tool_provider == "mcp" and settings.mcp_enabled:
        _mcp_process = await _start_mcp_subprocess(settings)

    if settings.model_preload_on_startup:
        try:
            from src.speech.asr import get_asr_model
            from src.speech.vad import get_vad_model

            if settings.vad_enabled:
                get_vad_model()
            get_asr_model()
            logger.info("Model preload completed")
        except Exception:
            logger.warning("Model preload failed; service will lazy-load on first request", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Release resources cleanly on app shutdown."""
    global _mcp_process

    # Terminate the MCP subprocess if we started it
    if _mcp_process is not None:
        try:
            _mcp_process.terminate()
            await asyncio.wait_for(_mcp_process.wait(), timeout=5)
            logger.info("MCP subprocess terminated pid=%s", _mcp_process.pid)
        except Exception:
            logger.warning("Failed to terminate MCP subprocess cleanly", exc_info=True)
        finally:
            _mcp_process = None

    try:
        from src.database import close_engine

        await close_engine()
    except Exception:
        logger.warning("Failed to dispose database engine cleanly", exc_info=True)


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "service": "Voice Chatbot",
        "status": "running",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    from src.speech.asr import is_asr_model_loaded
    from src.speech.vad import is_vad_model_loaded

    settings = get_settings()

    return {
        "status": "healthy",
        "components": {
            "chatbot": "ready",
            "asr": "loaded" if is_asr_model_loaded() else "lazy",
            "vad": (
                "disabled"
                if not settings.vad_enabled
                else ("loaded" if is_vad_model_loaded() else "lazy")
            ),
        },
    }
