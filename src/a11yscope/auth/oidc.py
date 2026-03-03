"""OIDC client using authlib."""
from __future__ import annotations

import logging

from authlib.integrations.httpx_client import AsyncOAuth2Client

from a11yscope.config import get_settings

logger = logging.getLogger(__name__)

_oidc_client: AsyncOAuth2Client | None = None
_oidc_metadata: dict | None = None


async def get_oidc_client() -> AsyncOAuth2Client:
    """Return a configured OIDC client, fetching discovery metadata."""
    global _oidc_client, _oidc_metadata
    settings = get_settings()

    if _oidc_client is not None:
        return _oidc_client

    _oidc_client = AsyncOAuth2Client(
        client_id=settings.sso_oidc_client_id,
        client_secret=settings.sso_oidc_client_secret,
    )

    # Fetch discovery metadata
    if settings.sso_oidc_discovery_url:
        import httpx
        async with httpx.AsyncClient() as http:
            resp = await http.get(settings.sso_oidc_discovery_url)
            resp.raise_for_status()
            _oidc_metadata = resp.json()

    return _oidc_client


def get_oidc_metadata() -> dict | None:
    """Return cached OIDC discovery metadata."""
    return _oidc_metadata


def create_authorization_url(redirect_uri: str, state: str) -> str:
    """Build the OIDC authorization URL."""
    if not _oidc_metadata:
        raise RuntimeError("OIDC metadata not loaded — call get_oidc_client() first")

    auth_endpoint = _oidc_metadata["authorization_endpoint"]
    settings = get_settings()

    params = {
        "client_id": settings.sso_oidc_client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": "openid email profile",
        "state": state,
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{auth_endpoint}?{qs}"


async def exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange auth code for tokens and return userinfo."""
    if not _oidc_metadata:
        raise RuntimeError("OIDC metadata not loaded")

    settings = get_settings()
    token_endpoint = _oidc_metadata["token_endpoint"]
    userinfo_endpoint = _oidc_metadata.get("userinfo_endpoint")

    import httpx
    async with httpx.AsyncClient() as http:
        # Exchange code
        resp = await http.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.sso_oidc_client_id,
                "client_secret": settings.sso_oidc_client_secret,
            },
        )
        resp.raise_for_status()
        tokens = resp.json()

        # Get userinfo
        if userinfo_endpoint:
            access_token = tokens["access_token"]
            resp = await http.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()

        # Decode ID token as fallback
        from jose import jwt as jose_jwt
        id_token = tokens.get("id_token", "")
        claims = jose_jwt.get_unverified_claims(id_token)
        return claims
