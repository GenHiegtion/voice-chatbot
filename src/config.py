from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Provider
    llm_provider: Literal["openrouter", "ollama"] = "ollama"

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "openai/gpt-4o"

    # Ollama
    ollama_api_key: str = ""
    ollama_base_url: str = "https://ollama.com"
    ollama_model: str = "kimi-k2:1t-cloud"

    # ASR correction
    correction_llm_provider: Literal["openrouter", "ollama"] = "ollama"
    correction_model: str = "kimi-k2:1t-cloud"

    # VAD (Voice Activity Detection)
    vad_enabled: bool = True

    # Model cache directory (HuggingFace models, Silero VAD, etc.)
    # Default: ~/.cache/huggingface/hub
    hf_home: str = ""
    torch_home: str = ""

    # Runtime tuning
    asr_max_workers: int = 4
    cart_ttl_seconds: int = 3600
    model_preload_on_startup: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    app_timezone: str = "Asia/Ho_Chi_Minh"

    # Database (MySQL) — leave empty if not using database yet
    db_host: str = ""
    db_port: int = 3306
    db_user: str = ""
    db_password: str = ""
    db_name: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_model_cache_environment() -> None:
    """Configure model cache directories from settings.

    This keeps model artifacts on disk so restarts reuse existing cache.
    """
    import os

    settings = get_settings()

    if settings.hf_home:
        os.environ["HF_HOME"] = settings.hf_home

    if settings.torch_home:
        os.environ["TORCH_HOME"] = settings.torch_home


def _build_ollama_client_auth_kwargs(api_key: str) -> dict:
    """Build auth kwargs for ChatOllama clients.

    ChatOllama accepts httpx kwargs through client_kwargs/sync_client_kwargs/
    async_client_kwargs. We pass Authorization header when OLLAMA_API_KEY is set.
    """
    if not api_key:
        return {}

    headers = {"Authorization": f"Bearer {api_key}"}
    return {
        "client_kwargs": {"headers": headers},
        "sync_client_kwargs": {"headers": headers},
        "async_client_kwargs": {"headers": headers},
    }


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """Create the main LLM instance based on provider config."""
    settings = get_settings()

    if settings.llm_provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            openai_api_key=settings.openrouter_api_key,
            openai_api_base=settings.openrouter_base_url,
            temperature=0.3,
            max_retries=2,
        )
    else:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.3,
            **_build_ollama_client_auth_kwargs(settings.ollama_api_key),
        )


@lru_cache(maxsize=1)
def get_correction_llm() -> BaseChatModel:
    """Create a lighter LLM for ASR text correction."""
    settings = get_settings()

    if settings.correction_llm_provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.correction_model,
            openai_api_key=settings.openrouter_api_key,
            openai_api_base=settings.openrouter_base_url,
            temperature=0.1,
            max_retries=2,
        )
    else:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.correction_model,
            base_url=settings.ollama_base_url,
            temperature=0.1,
            **_build_ollama_client_auth_kwargs(settings.ollama_api_key),
        )
