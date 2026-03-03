# tests/test_queue_manager.py
import pytest
import asyncio
from unittest.mock import AsyncMock
from a11yscope.web.queue_manager import ScanQueueManager


@pytest.fixture
def manager():
    mgr = ScanQueueManager()
    # Override _execute_job so tests don't call the real audit runner
    async def noop_execute(job_id, **kwargs):
        mgr._jobs[job_id].status = "complete"
    mgr._execute_job = noop_execute
    return mgr


@pytest.fixture(autouse=True)
async def cleanup_tasks():
    """Cancel any lingering asyncio tasks created by the queue manager."""
    yield
    for task in asyncio.all_tasks():
        if task is not asyncio.current_task() and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass


@pytest.mark.asyncio
async def test_enqueue_creates_job(manager):
    """Enqueuing returns a job ID and the job is tracked."""
    job_id = await manager.enqueue(
        user_id="u1", api_key_id="k1", canvas_url="https://c.edu",
        course_id=101, course_name="CS101",
        db_session_factory=AsyncMock(),
        decrypt_fn=lambda kid: "plaintext-token",
    )
    assert isinstance(job_id, str)
    # Give worker time to process
    await asyncio.sleep(0.05)
    status = manager.get_job_status(job_id)
    assert status is not None
    assert status["status"] in ("queued", "running", "complete")


@pytest.mark.asyncio
async def test_sequential_per_key(manager):
    """Jobs with the same key run sequentially."""
    started = []

    async def slow_run(job_id, **kwargs):
        started.append(job_id)
        await asyncio.sleep(0.1)
        manager._jobs[job_id].status = "complete"

    manager._execute_job = slow_run

    id1 = await manager.enqueue(
        user_id="u1", api_key_id="k1", canvas_url="https://c.edu",
        course_id=1, course_name="C1",
        db_session_factory=AsyncMock(), decrypt_fn=lambda kid: "tok",
    )
    id2 = await manager.enqueue(
        user_id="u1", api_key_id="k1", canvas_url="https://c.edu",
        course_id=2, course_name="C2",
        db_session_factory=AsyncMock(), decrypt_fn=lambda kid: "tok",
    )
    await asyncio.sleep(0.05)
    assert started[0] == id1


@pytest.mark.asyncio
async def test_cancel_queued_job(manager):
    """Cancelling a queued job removes it."""
    async def block_briefly(job_id, **kwargs):
        await asyncio.sleep(0.5)
        manager._jobs[job_id].status = "complete"

    manager._execute_job = block_briefly
    id1 = await manager.enqueue(
        user_id="u1", api_key_id="k1", canvas_url="https://c.edu",
        course_id=1, course_name="C1",
        db_session_factory=AsyncMock(), decrypt_fn=lambda kid: "tok",
    )
    cancelled = manager.cancel(id1)
    assert cancelled is True
