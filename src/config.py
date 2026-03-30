from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Provider
    llm_provider: Literal["openrouter", "ollama"] = "openrouter"

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "openai/gpt-4o"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # ASR correction
    correction_llm_provider: Literal["openrouter", "ollama"] = "openrouter"
    correction_model: str = "openai/gpt-4o-mini"

    # VAD (Voice Activity Detection)
    vad_enabled: bool = True

    # Model cache directory (HuggingFace models, Silero VAD, etc.)
    # Default: ~/.cache/huggingface/hub
    hf_home: str = ""

    # Database (MySQL) — leave empty if not using database yet
    db_host: str = ""
    db_port: int = 3306
    db_user: str = ""
    db_password: str = ""
    db_name: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


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
        )
    else:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.3,
        )


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
        )
    else:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.correction_model,
            base_url=settings.ollama_base_url,
            temperature=0.1,
        )
