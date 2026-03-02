"""Canvas Accessibility Auditor CLI."""
import asyncio
import json
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import check modules to trigger registration
import canvas_a11y.checks.html_checks  # noqa: F401
import canvas_a11y.checks.contrast_check  # noqa: F401
import canvas_a11y.checks.pdf_check  # noqa: F401
import canvas_a11y.checks.document_check  # noqa: F401
import canvas_a11y.checks.image_check  # noqa: F401

from canvas_a11y.config import get_settings
from canvas_a11y.canvas.client import CanvasClient
from canvas_a11y.canvas.content_fetcher import ContentFetcher
from canvas_a11y.canvas.content_updater import ContentUpdater
from canvas_a11y.canvas.file_manager import FileManager
from canvas_a11y.checks.registry import get_all_checks
from canvas_a11y.scoring.engine import score_course
from canvas_a11y.reporting.console_report import print_report
from canvas_a11y.reporting.html_report import generate_html_report
from canvas_a11y.reporting.json_report import generate_json_report
from canvas_a11y.remediation.autofix import AutoFixer
from canvas_a11y.remediation.ai_remediator import AIRemediator
from canvas_a11y.remediation.document_pipeline import DocumentPipeline
from canvas_a11y.models import CourseAuditResult


console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Canvas Accessibility Auditor — WCAG 2.1 AA compliance checker."""
    pass


@cli.command()
@click.option("--course-id", type=int, help="Canvas course ID to audit")
@click.option("--token", envvar="CA11Y_CANVAS_API_TOKEN", help="Canvas API token")
@click.option("--base-url", envvar="CA11Y_CANVAS_BASE_URL", default=None, help="Canvas base URL")
@click.option("--auto-fix", is_flag=True, help="Apply safe auto-fixes")
@click.option("--ai", is_flag=True, help="Use Claude AI for remediation")
@click.option("--apply", is_flag=True, help="Push fixes back to Canvas (required with --auto-fix)")
@click.option("--dry-run", is_flag=True, help="Show what would be fixed without applying")
@click.option("--no-confirm", is_flag=True, help="Skip fix confirmation prompts")
@click.option("--output-dir", type=click.Path(), default="output", help="Output directory")
@click.option("--format", "output_format", type=click.Choice(["console", "html", "json", "all"]), default="all", help="Report format")
def audit(course_id, token, base_url, auto_fix, ai, apply, dry_run, no_confirm, output_dir, output_format):
    """Audit a Canvas course for accessibility compliance."""
    settings = get_settings()
    if token:
        settings.canvas_api_token = token
    if base_url:
        settings.canvas_base_url = base_url

    if not settings.canvas_api_token:
        console.print("[red]Error: Canvas API token required. Set CA11Y_CANVAS_API_TOKEN or use --token[/red]")
        raise SystemExit(1)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    asyncio.run(_audit(settings, course_id, auto_fix, ai, apply, dry_run, no_confirm, output_path, output_format))


async def _audit(settings, course_id, auto_fix, ai, apply, dry_run, no_confirm, output_path, output_format):
    """Async audit implementation."""
    async with CanvasClient(
        settings.canvas_base_url,
        settings.canvas_api_token,
        rate_limit_delay=settings.rate_limit_delay,
        timeout=settings.request_timeout,
    ) as client:
        # If no course ID, show course picker
        if not course_id:
            course_id = await _pick_course(client)
            if not course_id:
                return

        # Get course info
        course = await client.get_course(course_id)
        course_name = course.get("name", f"Course {course_id}")
        console.print(f"\n[bold]Auditing: {course_name}[/bold] (ID: {course_id})\n")

        # Fetch content
        fetcher = ContentFetcher(client, course_id)
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            content_items, file_items = await fetcher.fetch_all(progress)

        console.print(f"Found {len(content_items)} content items and {len(file_items)} files\n")

        # Run checks on content
        checks = get_all_checks()
        console.print(f"Running {len(checks)} accessibility checks...")

        for item in content_items:
            if not item.html_content:
                continue
            for check in checks:
                issues = check.check_html(item.html_content, item.url)
                item.issues.extend(issues)

        # Download and check files (only PDFs, DOCX, PPTX, images under size limit)
        file_manager = FileManager(client, course_id, output_path)
        checkable_extensions = {".pdf", ".docx", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".svg"}
        max_size = settings.max_file_size_mb * 1024 * 1024

        for file_item in file_items:
            ext = Path(file_item.filename).suffix.lower()
            if ext not in checkable_extensions:
                continue
            if file_item.size > max_size:
                console.print(f"  [yellow]Skipping {file_item.display_name} ({file_item.size // 1024 // 1024}MB > {settings.max_file_size_mb}MB limit)[/yellow]")
                continue
            try:
                local_path = await file_manager.download_file(file_item)
                for check in checks:
                    if hasattr(check, "check_file"):
                        issues = check.check_file(local_path)
                        file_item.issues.extend(issues)
            except Exception as e:
                console.print(f"  [yellow]Could not check {file_item.display_name}: {e}[/yellow]")

        # Build result
        result = CourseAuditResult(
            course_id=course_id,
            course_name=course_name,
            audit_timestamp=datetime.now(),
            content_items=content_items,
            file_items=[f for f in file_items if f.issues],  # only include files with issues
        )

        # Score
        score_course(result)

        # Auto-fix
        if auto_fix:
            fixer = AutoFixer(console=console, no_confirm=no_confirm)

            if ai and settings.anthropic_api_key:
                # AI-assisted fixes could be added here
                pass

            for item in result.content_items:
                fixed_html = fixer.fix_content_item(item, dry_run=dry_run or not apply)
                if fixed_html and apply and not dry_run:
                    updater = ContentUpdater(client, course_id)
                    success = await updater.update_content(item, fixed_html)
                    if success:
                        console.print(f"  [green]Updated in Canvas: {item.title}[/green]")
                    item.html_content = fixed_html

            # Re-score after fixes
            score_course(result)

        # Reports
        if output_format in ("console", "all"):
            print_report(result, console)

        reports_dir = output_path / "reports"
        if output_format in ("html", "all"):
            html_path = generate_html_report(result, reports_dir / f"audit_{course_id}.html")
            console.print(f"[dim]HTML report: {html_path}[/dim]")

        if output_format in ("json", "all"):
            json_path = generate_json_report(result, reports_dir / f"audit_{course_id}.json")
            console.print(f"[dim]JSON report: {json_path}[/dim]")


async def _pick_course(client: CanvasClient) -> int | None:
    """Interactive course picker."""
    console.print("Fetching your courses...")
    courses = await client.get_courses()

    if not courses:
        console.print("[red]No courses found. Check your API token permissions.[/red]")
        return None

    console.print("\n[bold]Your Courses:[/bold]")
    for i, course in enumerate(courses, 1):
        console.print(f"  {i}. {course.get('name', 'Unknown')} (ID: {course['id']})")

    console.print()
    choice = click.prompt("Select a course number", type=int)
    if 1 <= choice <= len(courses):
        return courses[choice - 1]["id"]

    console.print("[red]Invalid selection.[/red]")
    return None


@cli.command()
@click.option("--course-id", type=int, required=True, help="Canvas course ID")
@click.option("--token", envvar="CA11Y_CANVAS_API_TOKEN", help="Canvas API token")
@click.option("--ai", is_flag=True, help="Use Claude AI for analysis")
@click.option("--output-dir", type=click.Path(), default="output", help="Output directory")
def remediate(course_id, token, ai, output_dir):
    """Download and remediate non-compliant documents."""
    settings = get_settings()
    if token:
        settings.canvas_api_token = token

    if not settings.canvas_api_token:
        console.print("[red]Error: Canvas API token required.[/red]")
        raise SystemExit(1)

    output_path = Path(output_dir)
    asyncio.run(_remediate(settings, course_id, ai, output_path))


async def _remediate(settings, course_id, use_ai, output_path):
    """Async remediation implementation."""
    async with CanvasClient(
        settings.canvas_base_url,
        settings.canvas_api_token,
        rate_limit_delay=settings.rate_limit_delay,
        timeout=settings.request_timeout,
    ) as client:
        # Fetch files
        fetcher = ContentFetcher(client, course_id)
        _, file_items = await fetcher.fetch_all()

        # Run file checks
        checks = get_all_checks()
        file_manager = FileManager(client, course_id, output_path)
        checkable_extensions = {".pdf", ".docx", ".pptx"}

        for file_item in file_items:
            ext = Path(file_item.filename).suffix.lower()
            if ext not in checkable_extensions:
                continue
            try:
                local_path = await file_manager.download_file(file_item)
                for check in checks:
                    if hasattr(check, "check_file"):
                        issues = check.check_file(local_path)
                        file_item.issues.extend(issues)
            except Exception as e:
                console.print(f"  [yellow]Could not check {file_item.display_name}: {e}[/yellow]")

        # Setup AI if requested
        ai_remediator = None
        if use_ai and settings.anthropic_api_key:
            ai_remediator = AIRemediator(settings.anthropic_api_key)

        # Run pipeline
        pipeline = DocumentPipeline(client, course_id, output_path, ai_remediator, console)
        manifest = await pipeline.remediate_files(file_items)

        if manifest:
            pipeline.save_manifest(manifest)
            console.print(f"\n[bold green]Remediation complete! {len(manifest)} files processed.[/bold green]")
            console.print(f"Run [bold]canvas-a11y upload --course-id {course_id} --manifest {output_path}/reupload_manifest.json[/bold] to push fixes.")
        else:
            console.print("[green]No files needed remediation.[/green]")


@cli.command()
@click.option("--course-id", type=int, required=True, help="Canvas course ID")
@click.option("--token", envvar="CA11Y_CANVAS_API_TOKEN", help="Canvas API token")
@click.option("--manifest", type=click.Path(exists=True), required=True, help="Path to reupload_manifest.json")
def upload(course_id, token, manifest):
    """Re-upload remediated files to Canvas."""
    settings = get_settings()
    if token:
        settings.canvas_api_token = token

    if not settings.canvas_api_token:
        console.print("[red]Error: Canvas API token required.[/red]")
        raise SystemExit(1)

    asyncio.run(_upload(settings, course_id, manifest))


async def _upload(settings, course_id, manifest_path):
    """Async upload implementation."""
    with open(manifest_path) as f:
        manifest = json.load(f)

    files_to_upload = [f for f in manifest.get("files", []) if f.get("status") == "remediated" and f.get("remediated")]

    if not files_to_upload:
        console.print("[yellow]No remediated files to upload.[/yellow]")
        return

    async with CanvasClient(
        settings.canvas_base_url,
        settings.canvas_api_token,
        rate_limit_delay=settings.rate_limit_delay,
        timeout=settings.request_timeout,
    ) as client:
        file_manager = FileManager(client, course_id, Path("output"))

        console.print(f"\n[bold]Uploading {len(files_to_upload)} remediated files...[/bold]")

        for entry in files_to_upload:
            local_path = Path(entry["remediated"])
            if not local_path.exists():
                console.print(f"  [red]File not found: {local_path}[/red]")
                continue

            from canvas_a11y.models import FileItem
            file_item = FileItem(
                id=entry["file_id"],
                display_name=entry["display_name"],
                filename=local_path.name,
                content_type_header="application/octet-stream",
                size=local_path.stat().st_size,
                url="",
            )

            try:
                result = await file_manager.upload_file(file_item, local_path)
                console.print(f"  [green]Uploaded: {entry['display_name']}[/green]")
            except Exception as e:
                console.print(f"  [red]Failed to upload {entry['display_name']}: {e}[/red]")

        console.print("\n[bold green]Upload complete![/bold green]")
