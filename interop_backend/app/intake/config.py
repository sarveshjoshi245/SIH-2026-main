"""
Configuration module for the RAG Intake & Decision Engine.

Loads settings from environment variables / .env file.
Supports multiple LLM providers (OpenAI, Google, Anthropic) via abstraction.
"""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env from the rag-service root
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)


class Settings(BaseModel):
    """Application settings loaded from environment."""

    # LLM provider settings
    llm_provider: str = Field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "google")
    )
    llm_model: str = Field(
        default_factory=lambda: os.getenv("LLM_MODEL", "gemini-2.0-flash")
    )
    llm_api_key: str = Field(
        default_factory=lambda: os.getenv("LLM_API_KEY", "")
    )
    llm_temperature: float = Field(
        default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.1"))
    )

    # Embedding settings
    embedding_model: str = Field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
    )

    # Paths
    knowledge_base_path: str = Field(
        default_factory=lambda: os.getenv(
            "KNOWLEDGE_BASE_PATH",
            str(Path(__file__).resolve().parent.parent.parent / "knowledge")
        )
    )
    faiss_index_path: str = Field(
        default_factory=lambda: os.getenv(
            "FAISS_INDEX_PATH",
            str(Path(__file__).parent.parent / "faiss_index")
        )
    )

    # Server
    host: str = Field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = Field(
        default_factory=lambda: int(os.getenv("PORT", "8000"))
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


def get_llm():
    """
    Get a LangChain LLM instance based on the configured provider.
    Supports: openai, google, anthropic.
    """
    settings = get_settings()

    if settings.llm_provider.lower() == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            temperature=settings.llm_temperature,
        )
    elif settings.llm_provider.lower() == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.llm_api_key,
            temperature=settings.llm_temperature,
        )
    elif settings.llm_provider.lower() == "anthropic":
        from langchain_community.chat_models import ChatAnthropic
        return ChatAnthropic(
            model=settings.llm_model,
            anthropic_api_key=settings.llm_api_key,
            temperature=settings.llm_temperature,
        )
    else:
        raise ValueError(
            f"Unsupported LLM provider: {settings.llm_provider}. "
            f"Supported: openai, google, anthropic"
        )

