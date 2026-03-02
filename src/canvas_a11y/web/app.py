"""FastAPI application — serves API + static files."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from canvas_a11y.web.api.config_routes import router as config_router
from canvas_a11y.web.api.course_routes import router as course_router
from canvas_a11y.web.api.audit_routes import router as audit_router
from canvas_a11y.web.api.fix_routes import router as fix_router
from canvas_a11y.web.api.report_routes import router as report_router
from canvas_a11y.web.api.ws import router as ws_router

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Canvas A11Y Audit",
    description="WCAG 2.1 AA accessibility auditor for Canvas LMS",
    version="0.1.0",
)

# API routes
app.include_router(config_router, prefix="/api")
app.include_router(course_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(fix_router, prefix="/api")
app.include_router(report_router, prefix="/api")
app.include_router(ws_router)

# Static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    """Serve the SPA."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    """Entry point for `canvas-a11y-web` script."""
    import uvicorn
    uvicorn.run("canvas_a11y.web.app:app", host="0.0.0.0", port=8080, reload=False)
