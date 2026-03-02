"""Application configuration via environment variables and .env file."""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ACCESSIFLOW_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    canvas_base_url: str = "https://canvas.jccc.edu"
    canvas_api_token: str = ""
    output_dir: Path = Path("output")
    max_file_size_mb: int = 50
    rate_limit_delay: float = 0.25  # 250ms between API calls
    request_timeout: float = 30.0

    # AI provider settings (optional — BYO key)
    ai_provider: str = ""
    ai_api_key: str = ""
    ai_model: str = ""


def get_settings(**overrides) -> Settings:
    return Settings(**overrides)
