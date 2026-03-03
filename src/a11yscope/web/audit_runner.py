"""Adapts the CLI audit logic for the web GUI with progress callbacks."""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Coroutine

# Import check modules to trigger registration
import a11yscope.checks.html_checks  # noqa: F401
import a11yscope.checks.contrast_check  # noqa: F401
import a11yscope.checks.pdf_check  # noqa: F401
import a11yscope.checks.document_check  # noqa: F401
import a11yscope.checks.image_check  # noqa: F401

from a11yscope.canvas.client import CanvasClient
from a11yscope.canvas.content_fetcher import ContentFetcher
from a11yscope.canvas.content_updater import ContentUpdater
from a11yscope.canvas.file_manager import FileManager
from a11yscope.checks.registry import get_all_checks
from a11yscope.models import CourseAuditResult, ContentItem, FileItem
from a11yscope.remediation.autofix import AutoFixer
from a11yscope.scoring.engine import score_course

from a11yscope.web.session import AuditJob, JobStatus

# Type alias for progress callback
ProgressCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


async def _noop_progress(msg: dict[str, Any]) -> None:
    pass


async def run_audit(
    job: AuditJob,
    canvas_base_url: str,
    canvas_api_token: str,
    output_path: Path = Path("output"),
    on_progress: ProgressCallback | None = None,
) -> CourseAuditResult:
    """Run a full audit, mirroring cli.py:_audit() but with progress callbacks."""
    emit = on_progress or _noop_progress
    job.status = JobStatus.RUNNING

    try:
        async with CanvasClient(
            canvas_base_url,
            canvas_api_token,
            rate_limit_delay=0.25,
            timeout=30.0,
        ) as client:
            # Phase: fetching
            await emit({"type": "phase", "phase": "fetching", "label": "Fetching course content..."})

            course = await client.get_course(job.course_id)
            job.course_name = course.get("name", f"Course {job.course_id}")

            fetcher = ContentFetcher(client, job.course_id)
            metadata = await fetcher.fetch_course_metadata()
            content_items, file_items = await fetcher.fetch_all()

            content_count = len(content_items)
            file_count = len(file_items)
            await emit({
                "type": "item_found",
                "count": content_count + file_count,
                "label": f"Found {content_count} content items, {file_count} files",
            })

            # Phase: checking
            checks = get_all_checks()
            await emit({"type": "phase", "phase": "checking", "label": f"Running {len(checks)} checks..."})

            checked = 0
            total = len([i for i in content_items if i.html_content])
            for item in content_items:
                if not item.html_content:
                    continue
                for check in checks:
                    issues = check.check_html(item.html_content, item.url)
                    item.issues.extend(issues)
                checked += 1
                await emit({
                    "type": "item_checked",
                    "title": item.title,
                    "issues": len(item.issues),
                    "checked": checked,
                    "total": total,
                })

            # Phase: files
            checkable_extensions = {".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".bmp", ".webp", ".tiff", ".tif"}
            max_size = 50 * 1024 * 1024  # 50MB
            file_manager = FileManager(client, job.course_id, output_path)
            files_to_check = [
                f for f in file_items
                if Path(f.filename).suffix.lower() in checkable_extensions and f.size <= max_size
            ]

            if files_to_check:
                await emit({"type": "phase", "phase": "files", "label": f"Checking {len(files_to_check)} files..."})

                for file_item in files_to_check:
                    try:
                        local_path = await file_manager.download_file(file_item)
                        for check in checks:
                            if hasattr(check, "check_file"):
                                issues = check.check_file(local_path)
                                file_item.issues.extend(issues)
                        await emit({
                            "type": "file_checked",
                            "name": file_item.display_name,
                            "issues": len(file_item.issues),
                        })
                    except Exception:
                        pass

            # Phase: scoring
            await emit({"type": "phase", "phase": "scoring", "label": "Calculating scores..."})

            result = CourseAuditResult(
                course_id=job.course_id,
                course_name=job.course_name,
                audit_timestamp=datetime.now(),
                content_items=content_items,
                file_items=[f for f in file_items if f.issues],
                course_code=metadata.get("course_code", ""),
                term_name=metadata.get("term_name", ""),
                instructor_name=metadata.get("instructor_name", ""),
                instructor_email=metadata.get("instructor_email", ""),
                enrollment_count=metadata.get("enrollment_count", 0),
                department=metadata.get("department", ""),
            )
            score_course(result)

            # Done
            job.result = result
            job.status = JobStatus.COMPLETE
            await emit({
                "type": "complete",
                "score": result.overall_score,
                "total_issues": result.total_issues,
            })
            return result

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        await emit({"type": "error", "message": str(e)})
        raise


async def apply_fixes(
    job: AuditJob,
    canvas_base_url: str,
    canvas_api_token: str,
    issue_indices: list[int] | None = None,
    push_to_canvas: bool = False,
) -> tuple[int, float | None, list[str]]:
    """Apply auto-fixes to the audit result. Returns (fixed_count, new_score, errors)."""
    if not job.result:
        return 0, None, ["No audit result to fix"]

    fixer = AutoFixer(no_confirm=True)
    fixed_count = 0
    errors: list[str] = []

    async with CanvasClient(
        canvas_base_url,
        canvas_api_token,
        rate_limit_delay=0.25,
        timeout=30.0,
    ) as client:
        for item in job.result.content_items:
            fixable = [i for i in item.issues if i.auto_fixable and not i.fixed]
            if not fixable:
                continue

            try:
                fixed_html = fixer.fix_content_item(item, dry_run=not push_to_canvas)
                if fixed_html:
                    if push_to_canvas:
                        updater = ContentUpdater(client, job.course_id)
                        await updater.update_content(item, fixed_html)
                        item.html_content = fixed_html
                    fixed_count += sum(1 for i in item.issues if i.fixed)
            except Exception as e:
                errors.append(f"Error fixing {item.title}: {e}")

    # Re-score
    score_course(job.result)
    return fixed_count, job.result.overall_score, errors
