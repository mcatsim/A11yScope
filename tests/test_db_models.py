"""Tests for SQLAlchemy ORM models: ApiKey, AuditJob, AuditJobItem.

Covers:
- ApiKey creation and encrypted_token storage as bytes
- AuditJob default status/progress and FK to ApiKey
- AuditJobItem cascade delete when parent job is deleted
"""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from a11yscope.db.models import Base, ApiKey, AuditJob, AuditJobItem


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_api_key_model(db_session):
    """ApiKey model stores encrypted token as bytes."""
    key = ApiKey(
        user_id="user-1",
        name="My Token",
        canvas_url="https://canvas.example.edu",
        encrypted_token=b"encrypted-bytes-here",
        token_hint="x123",
    )
    db_session.add(key)
    await db_session.commit()
    await db_session.refresh(key)
    assert key.id is not None
    assert key.encrypted_token == b"encrypted-bytes-here"
    assert key.token_hint == "x123"


@pytest.mark.asyncio
async def test_audit_job_model(db_session):
    """AuditJob persists scan state."""
    key = ApiKey(
        user_id="user-1",
        name="T",
        canvas_url="https://c.edu",
        encrypted_token=b"enc",
        token_hint="hint",
    )
    db_session.add(key)
    await db_session.commit()
    await db_session.refresh(key)

    job = AuditJob(
        user_id="user-1",
        api_key_id=key.id,
        canvas_url="https://c.edu",
        course_id=101,
        course_name="CS101",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    assert job.status == "queued"
    assert job.progress_pct == 0


@pytest.mark.asyncio
async def test_audit_job_items_cascade_delete(db_session):
    """Deleting a job cascades to its items."""
    key = ApiKey(
        user_id="u1",
        name="T",
        canvas_url="https://c.edu",
        encrypted_token=b"e",
        token_hint="h",
    )
    db_session.add(key)
    await db_session.commit()
    await db_session.refresh(key)

    job = AuditJob(
        user_id="u1",
        api_key_id=key.id,
        canvas_url="https://c.edu",
        course_id=1,
        course_name="C",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    item = AuditJobItem(
        job_id=job.id,
        item_type="page",
        item_title="Syllabus",
        sort_order=0,
    )
    db_session.add(item)
    await db_session.commit()

    await db_session.delete(job)
    await db_session.commit()

    result = await db_session.execute(select(AuditJobItem))
    assert result.scalars().all() == []
