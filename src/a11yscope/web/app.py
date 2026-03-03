"""FastAPI application — serves API + static files."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from a11yscope.web.api.config_routes import router as config_router
from a11yscope.web.api.course_routes import router as course_router
from a11yscope.web.api.audit_routes import router as audit_router
from a11yscope.web.api.fix_routes import router as fix_router
from a11yscope.web.api.report_routes import router as report_router
from a11yscope.web.api.ws import router as ws_router
from a11yscope.web.api.ai_routes import router as ai_router
from a11yscope.web.api.standards_routes import router as standards_router
from a11yscope.web.api.auth_routes import router as auth_router
from a11yscope.web.api.admin_routes import router as admin_router
from a11yscope.web.api.key_routes import router as key_router
from a11yscope.web.api.scan_routes import router as scan_router

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, run migrations, seed admin. Shutdown: dispose engine."""
    from a11yscope.db.engine import dispose_engine, init_db
    from a11yscope.db.seed import seed_admin
    from a11yscope.db.session import get_session_factory

    # Create tables (SQLite auto-create; PG should use Alembic)
    await init_db()
    logger.info("Database initialized")

    # Seed admin user
    factory = get_session_factory()
    async with factory() as session:
        await seed_admin(session)

    # Initialize scan queue manager
    from a11yscope.web.queue_manager import ScanQueueManager
    from a11yscope.web.api.scan_routes import set_queue_manager
    queue_manager = ScanQueueManager()
    set_queue_manager(queue_manager)

    yield

    # Shutdown
    await dispose_engine()


app = FastAPI(
    title="A11yScope",
    description="WCAG 2.1 AA, Section 508, and VPAT accessibility auditor for Canvas LMS",
    version="2.0.0",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from a11yscope.auth.middleware import RequestIDMiddleware  # noqa: E402
app.add_middleware(RequestIDMiddleware)

from a11yscope.web.middleware.security_headers import SecurityHeadersMiddleware  # noqa: E402
app.add_middleware(SecurityHeadersMiddleware)

# API routes
app.include_router(auth_router, prefix="/api/auth")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(config_router, prefix="/api")
app.include_router(course_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(fix_router, prefix="/api")
app.include_router(report_router, prefix="/api")
app.include_router(ws_router)
app.include_router(ai_router, prefix="/api")
app.include_router(standards_router, prefix="/api")
app.include_router(key_router, prefix="/api")
app.include_router(scan_router, prefix="/api")

# Static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    """Serve the SPA."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


def main():
    """Entry point for `a11yscope-web` script."""
    import uvicorn
    uvicorn.run("a11yscope.web.app:app", host="0.0.0.0", port=8080, reload=False)  # nosec B104 — intentional for Docker
