"""Rich terminal output for accessibility audit results."""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from canvas_a11y.models import CourseAuditResult, Severity


def _score_color(score: float | None) -> str:
    if score is None:
        return "dim"
    if score >= 90:
        return "green"
    elif score >= 70:
        return "yellow"
    else:
        return "red"


def _severity_style(severity: Severity) -> str:
    return {
        Severity.CRITICAL: "bold red",
        Severity.SERIOUS: "red",
        Severity.MODERATE: "yellow",
        Severity.MINOR: "dim",
    }.get(severity, "white")


def print_report(result: CourseAuditResult, console: Console | None = None) -> None:
    """Print a formatted audit report to the terminal."""
    console = console or Console()

    # Header
    score = result.overall_score or 0
    score_color = _score_color(result.overall_score)
    console.print()
    console.print(Panel(
        f"[bold]Course:[/bold] {result.course_name} (ID: {result.course_id})\n"
        f"[bold]Score:[/bold] [{score_color}]{score:.1f}%[/{score_color}]\n"
        f"[bold]Status:[/bold] {'[green]PASSING' if score >= 90 else '[red]FAILING'}[/]\n"
        f"[bold]Items:[/bold] {result.items_passing} passing / {result.items_failing} failing\n"
        f"[bold]Issues:[/bold] {result.total_issues} total "
        f"({result.critical_count} critical, {result.serious_count} serious, "
        f"{result.moderate_count} moderate, {result.minor_count} minor)",
        title="[bold]Canvas Accessibility Audit[/bold]",
        border_style=score_color,
    ))

    # Content items table
    if result.content_items:
        table = Table(title="Content Items", show_lines=True)
        table.add_column("Type", style="cyan", width=12)
        table.add_column("Title", width=40)
        table.add_column("Score", justify="right", width=8)
        table.add_column("Issues", justify="right", width=8)

        for item in sorted(result.content_items, key=lambda x: x.score or 0):
            color = _score_color(item.score)
            table.add_row(
                item.content_type.value,
                item.title[:40],
                f"[{color}]{item.score:.1f}%[/{color}]" if item.score is not None else "---",
                str(len(item.issues)),
            )
        console.print(table)

    # File items table
    if result.file_items:
        table = Table(title="File Items", show_lines=True)
        table.add_column("File", width=40)
        table.add_column("Type", width=12)
        table.add_column("Score", justify="right", width=8)
        table.add_column("Issues", justify="right", width=8)

        for item in sorted(result.file_items, key=lambda x: x.score or 0):
            color = _score_color(item.score)
            table.add_row(
                item.display_name[:40],
                item.content_type_header[:12],
                f"[{color}]{item.score:.1f}%[/{color}]" if item.score is not None else "---",
                str(len(item.issues)),
            )
        console.print(table)

    # Detailed issues (grouped by severity)
    if result.total_issues > 0:
        console.print("\n[bold]Issues Detail[/bold]")
        all_issues = []
        for item in result.content_items:
            for issue in item.issues:
                all_issues.append((item.title, issue))
        for item in result.file_items:
            for issue in item.issues:
                all_issues.append((item.display_name, issue))

        # Sort by severity
        severity_order = {Severity.CRITICAL: 0, Severity.SERIOUS: 1, Severity.MODERATE: 2, Severity.MINOR: 3}
        all_issues.sort(key=lambda x: severity_order.get(x[1].severity, 99))

        issue_table = Table(show_lines=False, pad_edge=False)
        issue_table.add_column("Sev", width=10)
        issue_table.add_column("Check", width=28)
        issue_table.add_column("Item", width=25)
        issue_table.add_column("Description", width=50)

        for item_name, issue in all_issues[:50]:  # Limit to 50 issues in console
            style = _severity_style(issue.severity)
            issue_table.add_row(
                f"[{style}]{issue.severity.value.upper()}[/{style}]",
                issue.check_id,
                item_name[:25],
                issue.description[:50],
            )

        console.print(issue_table)

        if len(all_issues) > 50:
            console.print(f"\n[dim]... and {len(all_issues) - 50} more issues (see full report)[/dim]")

    console.print()
