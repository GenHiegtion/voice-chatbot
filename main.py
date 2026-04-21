"""Voice Chatbot - FastAPI Application

AI Service for a food ordering app, including:
- Multi-Agent Chatbot (LangGraph) with Coordinator, Menu, Order, Promotion agents
- Vietnamese Speech-to-Text (ChunkFormer ASR)
- LLM post-processing text correction
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.lenient_json import LenientJSONMiddleware
from src.api.routes import chat, speech
from src.config import configure_model_cache_environment, get_settings


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


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize app-level resources once per process startup."""
    settings = get_settings()
    configure_model_cache_environment()

    from src.agents.graph import get_graph
    from src.database import probe_database_connection

    # Build graph early to avoid first-request latency.
    get_graph()
    logger.info("Graph initialized")

    db_ready = await probe_database_connection()
    logger.info("Database probe status=%s", "ready" if db_ready else "unavailable")

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
