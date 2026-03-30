"""Android AI Service - FastAPI Application

AI Service for a food ordering app, including:
- Multi-Agent Chatbot (LangGraph) with Coordinator, Menu, Order, Promotion agents
- Vietnamese Speech-to-Text (ChunkFormer ASR)
- LLM post-processing text correction
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import chat, speech

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Suppress noisy third-party loggers:
# - httpx: logs every HTTP request to HuggingFace Hub
# - huggingface_hub: unauthenticated warnings
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)

# Filter out ChunkFormer checkpoint loader spam ("missing/unexpected tensor", 300+ lines)


class _CheckpointLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "missing tensor:" in msg or "unexpected tensor:" in msg:
            return False
        return True


logging.getLogger().addFilter(_CheckpointLogFilter())

app = FastAPI(
    title="Android AI Service",
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

# Include routers
app.include_router(chat.router)
app.include_router(speech.router)


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "service": "Android AI Service",
        "status": "running",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "components": {
            "chatbot": "ready",
            "asr": "available",
        },
    }
