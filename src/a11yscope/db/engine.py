"""Async SQLAlchemy engine factory."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from a11yscope.config import get_settings

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """Return the singleton async engine, creating it if needed."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            future=True,
        )
    return _engine


async def dispose_engine() -> None:
    """Dispose the engine on shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


async def init_db() -> None:
    """Create all tables (for SQLite / dev). Production uses Alembic."""
    from a11yscope.db.models import Base

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
