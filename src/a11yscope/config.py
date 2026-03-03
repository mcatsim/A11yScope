"""Application configuration via environment variables and .env file."""
from __future__ import annotations

import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="A11YSCOPE_",
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

    # ── CORS ─────────────────────────────────────────────────────
    cors_origins: str = ""  # comma-separated origins, empty = same-origin only

    # ── Auth ────────────────────────────────────────────────────
    auth_mode: str = "none"  # none | local | sso
    secret_key: str = ""  # JWT signing; auto-generated if blank
    database_url: str = "sqlite+aiosqlite:///data/a11yscope.db"

    # Default admin (seeded on first boot when auth_mode != none)
    admin_email: str = "admin@localhost"
    admin_password: str = ""

    # Shared Canvas token (used when no per-user token)
    shared_canvas_token: str = ""

    # ── SSO (only when auth_mode=sso) ───────────────────────────
    sso_protocol: str = "oidc"  # oidc | saml
    sso_oidc_discovery_url: str = ""
    sso_oidc_client_id: str = ""
    sso_oidc_client_secret: str = ""
    sso_saml_metadata_url: str = ""
    sso_saml_entity_id: str = ""
    sso_default_role: str = "auditor"
    sso_auto_create_users: bool = True

    @property
    def effective_secret_key(self) -> str:
        """Return secret_key, generating a random one for auth_mode=none."""
        if self.secret_key:
            return self.secret_key
        if self.auth_mode == "none":
            return secrets.token_urlsafe(32)
        raise ValueError(
            "A11YSCOPE_SECRET_KEY is required when auth_mode is not 'none'"
        )


def get_settings(**overrides) -> Settings:
    return Settings(**overrides)
