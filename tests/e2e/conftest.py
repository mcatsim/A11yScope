"""E2E test fixtures — uses httpx ASGITransport for fast, reliable testing."""
import asyncio

import pytest
import httpx

from accessiflow.web.app import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def app_server():
    """Return the base URL for WebSocket tests using a real server."""
    # For HTTP tests we use ASGITransport (no real server needed).
    # For WebSocket tests we spin up a real server.
    import threading
    import uvicorn

    config = uvicorn.Config(app=app, host="127.0.0.1", port=18923, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for it to be ready
    import time
    for _ in range(50):
        time.sleep(0.1)
        if server.started:
            break

    yield "http://127.0.0.1:18923"
    server.should_exit = True
    thread.join(timeout=3)


@pytest.fixture
async def client():
    """Async HTTP client using ASGI transport — no real server needed."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=30.0) as c:
        yield c
