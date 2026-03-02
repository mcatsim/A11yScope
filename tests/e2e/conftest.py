"""E2E test fixtures — spins up the FastAPI app for integration testing."""
import asyncio
from contextlib import asynccontextmanager

import pytest
import httpx
from uvicorn import Config, Server


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def app_server(event_loop):
    """Start the real FastAPI app on a random port for E2E testing."""
    from canvas_a11y.web.app import app

    config = Config(app=app, host="127.0.0.1", port=0, log_level="warning")
    server = Server(config)

    # Let uvicorn pick an available port
    task = event_loop.create_task(server.serve())

    # Wait for server to start
    for _ in range(50):
        await asyncio.sleep(0.1)
        if server.started:
            break

    # Get the actual bound port
    sockets = server.servers
    port = None
    for s in sockets:
        for sock in s.sockets:
            addr = sock.getsockname()
            if addr:
                port = addr[1]
                break
        if port:
            break

    if not port:
        # Fallback: try the config port
        port = config.port

    base_url = f"http://127.0.0.1:{port}"
    yield base_url

    server.should_exit = True
    await task


@pytest.fixture
async def client(app_server):
    """Async HTTP client pointed at the running E2E server."""
    async with httpx.AsyncClient(base_url=app_server, timeout=30.0) as c:
        yield c
