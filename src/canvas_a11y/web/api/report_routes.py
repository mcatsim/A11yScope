"""Report download routes."""
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from canvas_a11y.reporting.html_report import generate_html_report
from canvas_a11y.reporting.json_report import generate_json_report
from canvas_a11y.web.session import get_or_create_default_session, get_job

router = APIRouter()
OUTPUT_DIR = Path("output/web_reports")


@router.get("/report/{job_id}/html")
async def download_html_report(job_id: str):
    """Generate and download the HTML report."""
    session = get_or_create_default_session()
    job = get_job(session, job_id)
    if not job or not job.result:
        raise HTTPException(status_code=404, detail="Audit result not found")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"audit_{job.course_id}_{job_id}.html"
    generate_html_report(job.result, out_path)
    return FileResponse(
        str(out_path),
        media_type="text/html",
        filename=f"a11y_audit_{job.course_id}.html",
    )


@router.get("/report/{job_id}/json")
async def download_json_report(job_id: str):
    """Generate and download the JSON report."""
    session = get_or_create_default_session()
    job = get_job(session, job_id)
    if not job or not job.result:
        raise HTTPException(status_code=404, detail="Audit result not found")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"audit_{job.course_id}_{job_id}.json"
    generate_json_report(job.result, out_path)
    return FileResponse(
        str(out_path),
        media_type="application/json",
        filename=f"a11y_audit_{job.course_id}.json",
    )
