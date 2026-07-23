"""Application configuration loaded from environment variables.

Single source of truth for all settings. Uses pydantic-settings for typed
access and .env file support.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── LLM Provider ───
    llm_provider: Literal["groq", "cerebras", "gemini"] = "groq"

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.1-8b-instant"

    cerebras_api_key: str = ""
    cerebras_base_url: str = "https://api.cerebras.ai/v1"
    cerebras_model: str = "llama-3.1-8b-instant"

    gemini_api_key: str = ""
    gemini_base_url: str = (
        "https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    gemini_model: str = "gemini-2.0-flash"

    # ─── Database ───
    database_url: str = (
        "postgresql+asyncpg://agentk:agentk@localhost:5432/agentk"
    )

    # ─── Embeddings ───
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ─── OpenTelemetry ───
    otel_exporter: Literal["console", "otlp"] = "console"
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_service_name: str = "rag-support-service"

    # ─── SigNoz ───
    signoz_base_url: str = "http://localhost:3301"

    # ─── App ───
    app_version: str = "v1"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # ─── Derived: active provider config ───
    @property
    def llm_api_key(self) -> str:
        return {
            "groq": self.groq_api_key,
            "cerebras": self.cerebras_api_key,
            "gemini": self.gemini_api_key,
        }[self.llm_provider]

    @property
    def llm_base_url(self) -> str:
        return {
            "groq": self.groq_base_url,
            "cerebras": self.cerebras_base_url,
            "gemini": self.gemini_base_url,
        }[self.llm_provider]

    @property
    def llm_model(self) -> str:
        return {
            "groq": self.groq_model,
            "cerebras": self.cerebras_model,
            "gemini": self.gemini_model,
        }[self.llm_provider]


@lru_cache
def get_settings() -> Settings:
    return Settings()
