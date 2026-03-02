"""E2E: WebSocket endpoint tests."""
import asyncio
import json

import pytest
import websockets


@pytest.mark.asyncio
async def test_ws_invalid_job_returns_error(app_server):
    """WebSocket connection with invalid job_id returns error message."""
    ws_url = app_server.replace("http://", "ws://") + "/ws/audit/nonexistent"
    async with websockets.connect(ws_url) as ws:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        assert msg["type"] == "error"
        assert "not found" in msg["message"].lower()
