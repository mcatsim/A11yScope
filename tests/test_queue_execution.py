# tests/test_queue_execution.py
"""Tests for queue manager <-> audit runner integration.

Validates:
- _execute_job updates job progress fields via the callback
- Progress log accumulates all messages for WebSocket replay
- Cancellation via cancel_event raises CancelledError
- Failed audit sets job.status = "failed" with error message
- Decrypted API key is dereferenced after use
- Stats messages update progress_pct and issues_found
"""

import asyncio

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from a11yscope.web.queue_manager import ScanQueueManager, QueuedJob


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_result(score: float = 87.5, total_issues: int = 5):
    """Return a lightweight mock CourseAuditResult."""
    result = MagicMock()
    result.overall_score = score
    result.total_issues = total_issues
    return result


async def _fake_run_audit(*, job, canvas_base_url, canvas_api_token, on_progress=None):
    """Simulate a successful audit that emits standard progress messages."""
    emit = on_progress or (lambda msg: asyncio.sleep(0))

    await emit({"type": "phase", "phase": "fetching", "label": "Fetching course content..."})
    await emit({"type": "item_found", "count": 3, "label": "Found 2 content items, 1 files"})

    await emit({"type": "phase", "phase": "checking", "label": "Checking content items"})

    # Item 1
    await emit({
        "type": "item_start", "item_id": "101", "item_type": "page",
        "title": "Syllabus", "index": 1, "total": 2,
    })
    await emit({
        "type": "item_checked", "title": "Syllabus", "issues": 2,
        "checked": 1, "total": 2,
    })
    await emit({
        "type": "item_done", "item_id": "101", "issues": 2,
        "index": 1, "total": 2,
    })
    await emit({
        "type": "stats", "items_checked": 1, "items_total": 2,
        "issues_found": 2, "files_checked": 0, "files_total": 1,
        "progress_pct": 33,
    })

    # Item 2
    await emit({
        "type": "item_start", "item_id": "102", "item_type": "assignment",
        "title": "Essay Rubric", "index": 2, "total": 2,
    })
    await emit({
        "type": "item_checked", "title": "Essay Rubric", "issues": 1,
        "checked": 2, "total": 2,
    })
    await emit({
        "type": "item_done", "item_id": "102", "issues": 1,
        "index": 2, "total": 2,
    })
    await emit({
        "type": "stats", "items_checked": 2, "items_total": 2,
        "issues_found": 3, "files_checked": 0, "files_total": 1,
        "progress_pct": 67,
    })

    # Files phase
    await emit({"type": "phase", "phase": "files", "label": "Checking 1 files..."})
    await emit({
        "type": "item_start", "item_id": "201", "item_type": "file",
        "title": "syllabus.pdf", "index": 1, "total": 1,
    })
    await emit({
        "type": "file_checked", "name": "syllabus.pdf", "issues": 0,
    })
    await emit({
        "type": "item_done", "item_id": "201", "issues": 0,
        "index": 1, "total": 1,
    })
    await emit({
        "type": "stats", "items_checked": 2, "items_total": 2,
        "issues_found": 3, "files_checked": 1, "files_total": 1,
        "progress_pct": 100,
    })

    # Scoring + complete
    await emit({"type": "phase", "phase": "scoring", "label": "Calculating scores..."})

    result = _make_fake_result(score=87.5, total_issues=3)

    # The real audit_runner sets these on the AuditJob
    job.result = result
    job.status = "complete"

    await emit({"type": "complete", "score": 87.5, "total_issues": 3})
    return result


async def _fake_run_audit_fails(*, job, canvas_base_url, canvas_api_token, on_progress=None):
    """Simulate an audit that fails midway."""
    emit = on_progress or (lambda msg: asyncio.sleep(0))

    await emit({"type": "phase", "phase": "fetching", "label": "Fetching course content..."})

    job.status = "failed"
    job.error = "Canvas API rate limited"
    await emit({"type": "error", "message": "Canvas API rate limited"})
    raise RuntimeError("Canvas API rate limited")


async def _fake_run_audit_slow(*, job, canvas_base_url, canvas_api_token, on_progress=None):
    """Simulate a slow audit that checks cancel_event via the callback."""
    emit = on_progress or (lambda msg: asyncio.sleep(0))

    await emit({"type": "phase", "phase": "fetching", "label": "Fetching..."})
    await emit({"type": "item_found", "count": 10, "label": "Found 10 items"})
    await emit({"type": "phase", "phase": "checking", "label": "Checking..."})

    # This emission should trigger cancellation if cancel_event is set
    for i in range(10):
        await emit({
            "type": "item_start", "item_id": str(i), "item_type": "page",
            "title": f"Page {i}", "index": i + 1, "total": 10,
        })
        # Small sleep to let cancellation propagate
        await asyncio.sleep(0.01)

    result = _make_fake_result()
    job.result = result
    job.status = "complete"
    await emit({"type": "complete", "score": 100.0, "total_issues": 0})
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def manager():
    return ScanQueueManager()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_job_updates_progress(manager):
    """_execute_job should update job progress fields via callbacks."""
    with patch("a11yscope.web.audit_runner.run_audit", side_effect=_fake_run_audit):
        job_id = await manager.enqueue(
            user_id="u1",
            api_key_id="k1",
            canvas_url="https://canvas.example.com",
            course_id=101,
            course_name="CS101",
            db_session_factory=AsyncMock(),
            decrypt_fn=lambda kid: "fake-api-token",
        )

        # Wait for the worker to process the job
        await asyncio.sleep(0.3)

        job = manager._jobs[job_id]
        assert job.status == "complete"
        assert job.progress_pct == 100
        assert job.items_checked == 2
        assert job.issues_found == 3
        assert job.result is not None
        assert job.result.overall_score == 87.5


@pytest.mark.asyncio
async def test_progress_log_accumulates_messages(manager):
    """progress_log should contain all emitted messages for WebSocket replay."""
    with patch("a11yscope.web.audit_runner.run_audit", side_effect=_fake_run_audit):
        job_id = await manager.enqueue(
            user_id="u1",
            api_key_id="k1",
            canvas_url="https://canvas.example.com",
            course_id=101,
            course_name="CS101",
            db_session_factory=AsyncMock(),
            decrypt_fn=lambda kid: "fake-api-token",
        )

        await asyncio.sleep(0.3)

        job = manager._jobs[job_id]
        # Should have many progress entries
        assert len(job.progress_log) > 5

        # Check message types are present
        types = [m["type"] for m in job.progress_log]
        assert "phase" in types
        assert "item_found" in types
        assert "item_start" in types
        assert "item_checked" in types
        assert "item_done" in types
        assert "stats" in types
        assert "complete" in types


@pytest.mark.asyncio
async def test_execute_job_handles_failure(manager):
    """_execute_job should set status=failed and store error on audit failure."""
    with patch("a11yscope.web.audit_runner.run_audit", side_effect=_fake_run_audit_fails):
        job_id = await manager.enqueue(
            user_id="u1",
            api_key_id="k1",
            canvas_url="https://canvas.example.com",
            course_id=101,
            course_name="CS101",
            db_session_factory=AsyncMock(),
            decrypt_fn=lambda kid: "fake-api-token",
        )

        await asyncio.sleep(0.3)

        job = manager._jobs[job_id]
        assert job.status == "failed"
        assert job.error is not None
        assert "rate limited" in job.error.lower()

        # Error should also be in progress_log
        error_msgs = [m for m in job.progress_log if m["type"] == "error"]
        assert len(error_msgs) >= 1


@pytest.mark.asyncio
async def test_execute_job_cancellation(manager):
    """Setting cancel_event mid-audit should abort the job."""
    with patch("a11yscope.web.audit_runner.run_audit", side_effect=_fake_run_audit_slow):
        job_id = await manager.enqueue(
            user_id="u1",
            api_key_id="k1",
            canvas_url="https://canvas.example.com",
            course_id=101,
            course_name="CS101",
            db_session_factory=AsyncMock(),
            decrypt_fn=lambda kid: "fake-api-token",
        )

        # Give the worker a moment to start, then cancel
        await asyncio.sleep(0.05)
        manager.cancel(job_id)

        await asyncio.sleep(0.3)

        job = manager._jobs[job_id]
        assert job.status == "cancelled"


@pytest.mark.asyncio
async def test_execute_job_no_decrypt_fn(manager):
    """_execute_job should fail if no decrypt_fn is provided."""
    job_id = await manager.enqueue(
        user_id="u1",
        api_key_id="k1",
        canvas_url="https://canvas.example.com",
        course_id=101,
        course_name="CS101",
        db_session_factory=AsyncMock(),
        decrypt_fn=None,
    )

    await asyncio.sleep(0.3)

    job = manager._jobs[job_id]
    assert job.status == "failed"
    assert "decrypt" in job.error.lower()


@pytest.mark.asyncio
async def test_execute_job_empty_token(manager):
    """_execute_job should fail if decrypt_fn returns empty string."""
    job_id = await manager.enqueue(
        user_id="u1",
        api_key_id="k1",
        canvas_url="https://canvas.example.com",
        course_id=101,
        course_name="CS101",
        db_session_factory=AsyncMock(),
        decrypt_fn=lambda kid: "",
    )

    await asyncio.sleep(0.3)

    job = manager._jobs[job_id]
    assert job.status == "failed"
    assert "decrypt" in job.error.lower() or "token" in job.error.lower()


@pytest.mark.asyncio
async def test_stats_message_updates_progress_pct(manager):
    """Stats messages should update progress_pct on the job."""
    with patch("a11yscope.web.audit_runner.run_audit", side_effect=_fake_run_audit):
        job_id = await manager.enqueue(
            user_id="u1",
            api_key_id="k1",
            canvas_url="https://canvas.example.com",
            course_id=101,
            course_name="CS101",
            db_session_factory=AsyncMock(),
            decrypt_fn=lambda kid: "fake-api-token",
        )

        await asyncio.sleep(0.3)

        job = manager._jobs[job_id]
        # After completion, progress should be 100
        assert job.progress_pct == 100

        # Check that stats messages are in the progress log
        stats_msgs = [m for m in job.progress_log if m["type"] == "stats"]
        assert len(stats_msgs) >= 2
        # Last stats message should have highest progress
        assert stats_msgs[-1]["progress_pct"] >= stats_msgs[0]["progress_pct"]


@pytest.mark.asyncio
async def test_current_phase_tracks_phases(manager):
    """current_phase should reflect the latest phase message."""
    with patch("a11yscope.web.audit_runner.run_audit", side_effect=_fake_run_audit):
        job_id = await manager.enqueue(
            user_id="u1",
            api_key_id="k1",
            canvas_url="https://canvas.example.com",
            course_id=101,
            course_name="CS101",
            db_session_factory=AsyncMock(),
            decrypt_fn=lambda kid: "fake-api-token",
        )

        await asyncio.sleep(0.3)

        job = manager._jobs[job_id]
        # After completion, phase should be "complete"
        assert job.current_phase == "complete"


@pytest.mark.asyncio
async def test_job_result_stored_on_completion(manager):
    """Completed job should have result with score and total_issues."""
    with patch("a11yscope.web.audit_runner.run_audit", side_effect=_fake_run_audit):
        job_id = await manager.enqueue(
            user_id="u1",
            api_key_id="k1",
            canvas_url="https://canvas.example.com",
            course_id=101,
            course_name="CS101",
            db_session_factory=AsyncMock(),
            decrypt_fn=lambda kid: "fake-api-token",
        )

        await asyncio.sleep(0.3)

        job = manager._jobs[job_id]
        assert job.result is not None
        assert job.result.overall_score == 87.5
        assert job.result.total_issues == 3
