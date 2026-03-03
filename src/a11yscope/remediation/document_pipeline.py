"""Document remediation pipeline -- download, analyze, fix, stage."""
import json
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from a11yscope.models import CourseAuditResult, FileItem, Severity
from a11yscope.canvas.client import CanvasClient
from a11yscope.canvas.file_manager import FileManager
from a11yscope.remediation.pdf_remediator import PDFRemediator


class DocumentPipeline:
    """Full pipeline for remediating non-compliant documents."""

    def __init__(
        self,
        client: CanvasClient,
        course_id: int,
        output_dir: Path,
        console: Console | None = None,
    ):
        self.file_manager = FileManager(client, course_id, output_dir)
        self.pdf_remediator = PDFRemediator()
        self.console = console or Console()
        self.output_dir = output_dir
        self.remediated_dir = output_dir / "remediated"
        self.remediated_dir.mkdir(parents=True, exist_ok=True)

    async def remediate_files(self, file_items: list[FileItem]) -> list[dict]:
        """Process all non-compliant files. Returns manifest entries."""
        non_compliant = [f for f in file_items if f.issues and any(
            i.severity in (Severity.CRITICAL, Severity.SERIOUS) for i in f.issues
        )]

        if not non_compliant:
            self.console.print("[green]No non-compliant files to remediate.[/green]")
            return []

        self.console.print(f"\n[bold]Remediating {len(non_compliant)} files...[/bold]")
        manifest = []

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console) as progress:
            for file_item in non_compliant:
                task = progress.add_task(f"Processing {file_item.display_name}...", total=None)
                try:
                    entry = await self._remediate_single(file_item)
                    if entry:
                        manifest.append(entry)
                except Exception as e:
                    self.console.print(f"  [red]Error processing {file_item.display_name}: {e}[/red]")
                finally:
                    progress.update(task, completed=True)

        return manifest

    async def _remediate_single(self, file_item: FileItem) -> dict | None:
        """Remediate a single file. Returns manifest entry or None."""
        # Download
        local_path = await self.file_manager.download_file(file_item)
        self.console.print(f"  Downloaded: {file_item.display_name}")

        suffix = local_path.suffix.lower()
        output_path = self.remediated_dir / file_item.filename

        if suffix == ".pdf":
            return await self._remediate_pdf(file_item, local_path, output_path)

        # For other file types, just flag for manual review
        return {
            "original": str(local_path),
            "remediated": None,
            "file_id": file_item.id,
            "display_name": file_item.display_name,
            "status": "needs_manual_review",
            "issues": [i.description for i in file_item.issues],
        }

    async def _remediate_pdf(self, file_item: FileItem, local_path: Path, output_path: Path) -> dict:
        """Remediate a PDF file."""
        language = "en"
        title = file_item.display_name.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()

        self.pdf_remediator.remediate_full(local_path, output_path, title=title, language=language)
        file_item.remediated_path = output_path
        self.console.print(f"  [green]Remediated: {file_item.display_name}[/green]")

        return {
            "original": str(local_path),
            "remediated": str(output_path),
            "file_id": file_item.id,
            "display_name": file_item.display_name,
            "status": "remediated",
            "fixes_applied": ["title", "language", "mark_info"],
        }

    def save_manifest(self, manifest: list[dict], path: Path | None = None) -> Path:
        """Save the reupload manifest to JSON."""
        manifest_path = path or self.output_dir / "reupload_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump({"files": manifest}, f, indent=2)
        self.console.print(f"\n[bold]Manifest saved: {manifest_path}[/bold]")
        return manifest_path
