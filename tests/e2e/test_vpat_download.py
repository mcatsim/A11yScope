"""E2E tests for VPAT download endpoint."""
from __future__ import annotations
import pytest
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from accessiflow.web.app import app
from accessiflow.web.session import get_or_create_default_session, create_job
from accessiflow.models import CourseAuditResult, ContentItem, ContentType, AccessibilityIssue, Severity


def _setup_job_with_result():
    """Create a session with a completed audit job."""
    session = get_or_create_default_session()
    session.validated = True
    job = create_job(session, course_id=100, course_name="Test Course")
    job.result = CourseAuditResult(
        course_id=100, course_name="Test Course",
        audit_timestamp=datetime.now(),
        content_items=[
            ContentItem(
                id=1, content_type=ContentType.PAGE, title="Test Page",
                url="http://test/page", html_content="<p>hello</p>",
                issues=[AccessibilityIssue(
                    check_id="alt-text-missing", title="Missing alt",
                    description="Test", severity=Severity.CRITICAL,
                    wcag_criterion="1.1.1",
                )],
                score=70.0,
            ),
        ],
        overall_score=70.0,
    )
    from accessiflow.web.session import JobStatus
    job.status = JobStatus.COMPLETE
    return job


@pytest.mark.asyncio
async def test_vpat_download():
    job = _setup_job_with_result()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/report/{job.job_id}/vpat")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        body = resp.text
        assert "VPAT" in body
        assert "Perceivable" in body
        assert "1.1.1" in body


@pytest.mark.asyncio
async def test_vpat_download_nonexistent_job():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/report/nonexistent/vpat")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_html_report_has_standards():
    job = _setup_job_with_result()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/report/{job.job_id}/html")
        assert resp.status_code == 200
        body = resp.text
        assert "Standards" in body
        assert "Accessiflow" in body
