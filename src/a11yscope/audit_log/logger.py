"""AuditLogger — dual-write to DB + JSONL file."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from a11yscope.auth.backend import AuthUser
from a11yscope.audit_log.schemas import AuditAction
from a11yscope.db.models import AuditLogEntry
from a11yscope.db.session import get_db

logger = logging.getLogger(__name__)

JSONL_DIR = Path("data")
JSONL_FILE = JSONL_DIR / "audit.jsonl"


class AuditLogger:
    """Writes audit log entries to both DB and JSONL file."""

    def __init__(self, db: AsyncSession, request: Request | None = None):
        self.db = db
        self.request = request

    async def log(
        self,
        action: str | AuditAction,
        user: AuthUser | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        detail: dict | str | None = None,
        status: str = "success",
    ) -> None:
        """Write an audit log entry."""
        ip_address = None
        user_agent = None
        if self.request:
            ip_address = self.request.client.host if self.request.client else None
            user_agent = self.request.headers.get("User-Agent", "")[:500]

        detail_str = json.dumps(detail) if isinstance(detail, dict) else detail

        # DB write
        entry = AuditLogEntry(
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            action=str(action),
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            detail=detail_str,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
        )
        self.db.add(entry)
        await self.db.commit()

        # JSONL write
        try:
            JSONL_DIR.mkdir(parents=True, exist_ok=True)
            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user.id if user else None,
                "user_email": user.email if user else None,
                "action": str(action),
                "resource_type": resource_type,
                "resource_id": str(resource_id) if resource_id is not None else None,
                "detail": detail if isinstance(detail, dict) else detail_str,
                "ip_address": ip_address,
                "status": status,
            }
            with open(JSONL_FILE, "a") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except Exception:
            logger.warning("Failed to write audit JSONL", exc_info=True)


async def get_audit_logger(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuditLogger:
    """FastAPI dependency — returns an AuditLogger bound to the current request."""
    return AuditLogger(db=db, request=request)
