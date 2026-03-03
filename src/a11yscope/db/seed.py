"""First-run admin seeding from environment variables."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from a11yscope.config import get_settings
from a11yscope.db.models import User

logger = logging.getLogger(__name__)


async def seed_admin(session: AsyncSession) -> None:
    """Create the default admin user if no users exist yet."""
    settings = get_settings()

    if settings.auth_mode == "none":
        return

    result = await session.execute(select(User).limit(1))
    if result.scalar_one_or_none() is not None:
        return  # Users already exist

    email = settings.admin_email
    password = settings.admin_password

    if not email or not password:
        logger.warning(
            "A11YSCOPE_ADMIN_EMAIL / A11YSCOPE_ADMIN_PASSWORD not set — "
            "skipping admin seed"
        )
        return

    from a11yscope.auth.password import hash_password

    admin = User(
        email=email,
        display_name="Admin",
        role="admin",
        password_hash=hash_password(password),
        must_change_password=True,
    )
    session.add(admin)
    await session.commit()
    logger.info("Seeded admin user: %s", email)
