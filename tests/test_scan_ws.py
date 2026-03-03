# tests/test_scan_ws.py
"""Tests for the WebSocket scan progress endpoint (first-message auth).

Validates:
- Connection rejected when non-auth message sent (CWE-598 fix)
- Connection rejected with invalid JWT token
- Job-not-found returns error and closes
- Reconnection replay sends existing progress_log
- Stream completes when job finishes
"""
import pytest
from unittest.mock import patch, MagicMock

from starlette.testclient import TestClient

from a11yscope.web.app import app
from a11yscope.web.queue_manager import ScanQueueManager, QueuedJob
from a11yscope.web.api.scan_routes import set_queue_manager
from a11yscope.config import Settings


def _make_settings(**overrides) -> Settings:
    """Create a Settings instance with test defaults."""
    defaults = {
        "auth_mode": "none",
        "secret_key": "test-secret-key-for-ws-tests",
    }
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.fixture
def queue_manager():
    """Set up a fresh queue manager for each test."""
    qm = ScanQueueManager()
    set_queue_manager(qm)
    yield qm
    set_queue_manager(None)


# ---------------------------------------------------------------------------
# Auth rejection tests (auth_mode = "local")
# ---------------------------------------------------------------------------


def test_ws_rejects_without_auth(queue_manager):
    """WebSocket must reject connections with no auth message when auth required."""
    settings = _make_settings(auth_mode="local")

    with patch("a11yscope.web.api.scan_ws.get_settings", return_value=settings):
        client = TestClient(app)
        with client.websocket_connect("/ws/scan/fake-job-id") as ws:
            # Send a non-auth message -- should get error back
            ws.send_json({"type": "ping"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "auth" in msg["message"].lower() or "Expected" in msg["message"]


def test_ws_rejects_invalid_token(queue_manager):
    """WebSocket must reject connections with an invalid JWT token."""
    settings = _make_settings(auth_mode="local")

    with patch("a11yscope.web.api.scan_ws.get_settings", return_value=settings), \
         patch("a11yscope.web.api.scan_ws.decode_access_token", return_value=None):
        client = TestClient(app)
        with client.websocket_connect("/ws/scan/fake-job-id") as ws:
            ws.send_json({"type": "auth", "token": "bad-token"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "invalid" in msg["message"].lower() or "Invalid" in msg["message"]


def test_ws_rejects_auth_missing_token(queue_manager):
    """Auth message without token field is rejected."""
    settings = _make_settings(auth_mode="local")

    with patch("a11yscope.web.api.scan_ws.get_settings", return_value=settings):
        client = TestClient(app)
        with client.websocket_connect("/ws/scan/fake-job-id") as ws:
            ws.send_json({"type": "auth"})  # no token field
            msg = ws.receive_json()
            assert msg["type"] == "error"


# ---------------------------------------------------------------------------
# No-auth mode (auth_mode = "none") — job resolution tests
# ---------------------------------------------------------------------------


def test_ws_job_not_found(queue_manager):
    """WebSocket returns error when job_id does not exist."""
    settings = _make_settings(auth_mode="none")

    with patch("a11yscope.web.api.scan_ws.get_settings", return_value=settings):
        client = TestClient(app)
        with client.websocket_connect("/ws/scan/nonexistent-job") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "not found" in msg["message"].lower()


def test_ws_replays_progress_log(queue_manager):
    """Reconnection replays all existing progress_log entries."""
    settings = _make_settings(auth_mode="none")

    # Manually create a completed job with progress entries
    job = QueuedJob(
        job_id="replay-job",
        user_id="anonymous",
        api_key_id="k1",
        canvas_url="https://canvas.example.com",
        course_id=101,
        course_name="Test Course",
        status="complete",
        progress_log=[
            {"type": "progress", "phase": "pages", "pct": 50},
            {"type": "progress", "phase": "pages", "pct": 100},
            {"type": "item_result", "item": "Page 1", "issues": 0},
        ],
    )
    queue_manager._jobs["replay-job"] = job

    with patch("a11yscope.web.api.scan_ws.get_settings", return_value=settings):
        client = TestClient(app)
        with client.websocket_connect("/ws/scan/replay-job") as ws:
            # Should receive all 3 progress_log entries
            msg1 = ws.receive_json()
            assert msg1["type"] == "progress"
            assert msg1["pct"] == 50

            msg2 = ws.receive_json()
            assert msg2["type"] == "progress"
            assert msg2["pct"] == 100

            msg3 = ws.receive_json()
            assert msg3["type"] == "item_result"
            assert msg3["item"] == "Page 1"


def test_ws_access_denied_wrong_user(queue_manager):
    """WebSocket denies access when authenticated user does not own the job."""
    settings = _make_settings(auth_mode="local")
    payload = {"sub": "user-2", "email": "u2@test.com", "role": "auditor", "type": "access"}

    # Job belongs to user-1
    job = QueuedJob(
        job_id="owned-job",
        user_id="user-1",
        api_key_id="k1",
        canvas_url="https://canvas.example.com",
        course_id=101,
        course_name="Test Course",
        status="running",
        progress_log=[],
    )
    queue_manager._jobs["owned-job"] = job

    with patch("a11yscope.web.api.scan_ws.get_settings", return_value=settings), \
         patch("a11yscope.web.api.scan_ws.decode_access_token", return_value=payload):
        client = TestClient(app)
        with client.websocket_connect("/ws/scan/owned-job") as ws:
            ws.send_json({"type": "auth", "token": "valid-token"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "denied" in msg["message"].lower() or "Access" in msg["message"]


def test_ws_accepts_valid_auth():
    """WebSocket accepts connection with valid auth message.

    Placeholder for integration test -- will be expanded in Task 15.
    """
    pass
