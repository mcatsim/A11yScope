"""Authentication routes — login, logout, refresh, me, change-password."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from a11yscope.auth.backend import AuthUser
from a11yscope.auth.dependencies import get_current_user
from a11yscope.auth.jwt import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
)
from a11yscope.auth.models import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    TokenRefreshResponse,
    UserInfo,
)
from a11yscope.auth.password import hash_password, verify_password
from a11yscope.audit_log.logger import AuditLogger, get_audit_logger
from a11yscope.audit_log.schemas import AuditAction
from a11yscope.config import get_settings
from a11yscope.db.models import RefreshToken, User
from a11yscope.db.session import get_db

router = APIRouter(tags=["auth"])


@router.post("/login")
async def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> LoginResponse:
    """Authenticate with email + password, return JWT."""
    settings = get_settings()
    if settings.auth_mode == "none":
        raise HTTPException(status_code=400, detail="Auth mode is 'none'")

    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if user is None or not user.password_hash:
        await audit.log(AuditAction.LOGIN_FAILED, detail={"email": req.email}, status="failure")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(req.password, user.password_hash):
        await audit.log(AuditAction.LOGIN_FAILED, detail={"email": req.email}, status="failure")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        await audit.log(AuditAction.LOGIN_FAILED, detail={"email": req.email, "reason": "inactive"}, status="failure")
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Create tokens
    access_token = create_access_token(user.id, user.email, user.role, user.must_change_password)
    raw_refresh, token_hash, expires_at = create_refresh_token()

    # Store refresh token
    rt = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )
    db.add(rt)

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # Set refresh token as HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/api/auth",
    )

    auth_user = AuthUser(id=user.id, email=user.email, display_name=user.display_name, role=user.role)
    await audit.log(AuditAction.LOGIN, user=auth_user)

    return LoginResponse(
        access_token=access_token,
        must_change_password=user.must_change_password,
    )


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> TokenRefreshResponse:
    """Exchange refresh cookie for a new access token."""
    raw = request.cookies.get("refresh_token")
    if not raw:
        raise HTTPException(status_code=401, detail="No refresh token")

    token_hash = hash_refresh_token(raw)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
        )
    )
    rt = result.scalar_one_or_none()
    if rt is None or rt.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Load user
    user_result = await db.execute(select(User).where(User.id == rt.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Rotate: revoke old, issue new
    rt.revoked = True
    new_raw, new_hash, new_expires = create_refresh_token()
    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=new_hash,
        expires_at=new_expires,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )
    db.add(new_rt)
    await db.commit()

    response.set_cookie(
        key="refresh_token",
        value=new_raw,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/api/auth",
    )

    access_token = create_access_token(user.id, user.email, user.role, user.must_change_password)

    auth_user = AuthUser(id=user.id, email=user.email, display_name=user.display_name, role=user.role)
    await audit.log(AuditAction.TOKEN_REFRESH, user=auth_user)

    return TokenRefreshResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Revoke refresh token and clear cookie."""
    raw = request.cookies.get("refresh_token")
    if raw:
        token_hash = hash_refresh_token(raw)
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        rt = result.scalar_one_or_none()
        if rt:
            rt.revoked = True
            await db.commit()

    response.delete_cookie("refresh_token", path="/api/auth")
    await audit.log(AuditAction.LOGOUT, user=user)
    return {"ok": True}


@router.get("/me")
async def me(user: AuthUser = Depends(get_current_user)) -> UserInfo:
    """Return the current user's info."""
    return UserInfo(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        must_change_password=user.must_change_password,
    )


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Change the current user's password."""
    if user.id == "anonymous":
        raise HTTPException(status_code=400, detail="Cannot change password in no-auth mode")

    result = await db.execute(select(User).where(User.id == user.id))
    db_user = result.scalar_one_or_none()
    if not db_user or not db_user.password_hash:
        raise HTTPException(status_code=400, detail="Password change not supported for SSO users")

    if not verify_password(req.current_password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    db_user.password_hash = hash_password(req.new_password)
    db_user.must_change_password = False
    await db.commit()

    await audit.log(AuditAction.PASSWORD_CHANGED, user=user)
    return {"ok": True}


# ── SSO Routes ──────────────────────────────────────────────────


async def _sso_login_or_create(
    db: AsyncSession,
    email: str,
    display_name: str,
    idp_subject: str,
    idp_provider: str,
    request: Request,
    response: Response,
    audit: AuditLogger,
) -> LoginResponse:
    """Shared logic for OIDC/SAML callback — find or create user, issue JWT."""
    settings = get_settings()

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        if not settings.sso_auto_create_users:
            raise HTTPException(status_code=403, detail="User not found and auto-creation is disabled")
        user = User(
            email=email,
            display_name=display_name or email.split("@")[0],
            role=settings.sso_default_role,
            idp_subject=idp_subject,
            idp_provider=idp_provider,
        )
        db.add(user)
        await db.flush()
    else:
        user.idp_subject = idp_subject
        user.idp_provider = idp_provider
        if display_name:
            user.display_name = display_name

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(user.id, user.email, user.role)
    raw_refresh, token_hash, expires_at = create_refresh_token()

    rt = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )
    db.add(rt)
    await db.commit()

    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/api/auth",
    )

    auth_user = AuthUser(id=user.id, email=user.email, display_name=user.display_name, role=user.role)
    await audit.log(AuditAction.LOGIN, user=auth_user, detail={"idp_provider": idp_provider})

    return LoginResponse(access_token=access_token)


@router.get("/sso/oidc/login")
async def oidc_login(request: Request):
    """Redirect to OIDC IdP authorization endpoint."""
    settings = get_settings()
    if settings.auth_mode != "sso" or settings.sso_protocol != "oidc":
        raise HTTPException(status_code=400, detail="OIDC SSO not configured")

    from a11yscope.auth.oidc import get_oidc_client, create_authorization_url

    await get_oidc_client()
    redirect_uri = str(request.url_for("oidc_callback"))

    import secrets as _secrets
    state = _secrets.token_urlsafe(32)

    url = create_authorization_url(redirect_uri, state)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url)


@router.get("/sso/oidc/callback")
async def oidc_callback(
    code: str,
    state: str = "",
    request: Request = None,
    response: Response = None,
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """OIDC authorization code callback."""
    from a11yscope.auth.oidc import exchange_code

    redirect_uri = str(request.url_for("oidc_callback"))
    userinfo = await exchange_code(code, redirect_uri)

    email = userinfo.get("email", "")
    display_name = userinfo.get("name", userinfo.get("preferred_username", ""))
    subject = userinfo.get("sub", email)

    if not email:
        raise HTTPException(status_code=400, detail="No email in OIDC userinfo")

    login_resp = await _sso_login_or_create(
        db=db,
        email=email,
        display_name=display_name,
        idp_subject=subject,
        idp_provider="oidc",
        request=request,
        response=response,
        audit=audit,
    )

    # Redirect to frontend with token as fragment
    from fastapi.responses import HTMLResponse
    return HTMLResponse(
        f'<script>localStorage.setItem("access_token","{login_resp.access_token}");'
        f'window.location.href="/";</script>'
    )


@router.get("/sso/saml/login")
async def saml_login(request: Request):
    """Redirect to SAML IdP."""
    settings = get_settings()
    if settings.auth_mode != "sso" or settings.sso_protocol != "saml":
        raise HTTPException(status_code=400, detail="SAML SSO not configured")

    from a11yscope.auth.saml import load_idp_metadata, create_authn_request

    await load_idp_metadata()
    acs_url = str(request.url_for("saml_acs"))
    url = create_authn_request(acs_url)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url)


@router.post("/sso/saml/acs")
async def saml_acs(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """SAML Assertion Consumer Service (ACS) endpoint."""
    form = await request.form()
    saml_response = form.get("SAMLResponse", "")
    if not saml_response:
        raise HTTPException(status_code=400, detail="Missing SAMLResponse")

    from a11yscope.auth.saml import parse_saml_response

    attrs = parse_saml_response(str(saml_response))

    email = attrs.get("email", "")
    if not email:
        raise HTTPException(status_code=400, detail="No email in SAML response")

    login_resp = await _sso_login_or_create(
        db=db,
        email=email,
        display_name=attrs.get("display_name", ""),
        idp_subject=attrs.get("subject", email),
        idp_provider="saml",
        request=request,
        response=response,
        audit=audit,
    )

    from fastapi.responses import HTMLResponse
    return HTMLResponse(
        f'<script>localStorage.setItem("access_token","{login_resp.access_token}");'
        f'window.location.href="/";</script>'
    )


@router.get("/sso/metadata")
async def sso_metadata():
    """Return current SSO configuration (non-sensitive)."""
    settings = get_settings()
    return {
        "auth_mode": settings.auth_mode,
        "sso_protocol": settings.sso_protocol if settings.auth_mode == "sso" else None,
        "oidc_discovery_url": settings.sso_oidc_discovery_url if settings.sso_protocol == "oidc" else None,
        "saml_entity_id": settings.sso_saml_entity_id if settings.sso_protocol == "saml" else None,
    }
