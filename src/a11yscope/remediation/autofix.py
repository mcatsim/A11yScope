"""Safe HTML auto-fix engine."""
import re
from bs4 import BeautifulSoup, Tag
from rich.console import Console
from rich.syntax import Syntax

from a11yscope.models import AccessibilityIssue, ContentItem


class AutoFixer:
    """Applies safe, reversible HTML fixes."""

    def __init__(self, console: Console | None = None, no_confirm: bool = False):
        self.console = console or Console()
        self.no_confirm = no_confirm
        self.auto_approve_all = False

    def fix_content_item(self, item: ContentItem, dry_run: bool = False) -> str | None:
        """Apply all auto-fixable fixes to a content item. Returns fixed HTML or None."""
        if not item.html_content:
            return None

        fixable = [i for i in item.issues if i.auto_fixable and not i.fixed]
        if not fixable:
            return None

        html = item.html_content
        applied = 0

        for issue in fixable:
            fix_func = self._get_fix_func(issue.check_id)
            if not fix_func:
                continue

            new_html = fix_func(html, issue)
            if new_html and new_html != html:
                if dry_run:
                    self._show_diff(item.title, issue, html, new_html)
                    applied += 1
                    continue

                approved = self._confirm_fix(item.title, issue, html, new_html)
                if approved:
                    html = new_html
                    issue.fixed = True
                    issue.fix_description = f"Auto-fixed: {issue.check_id}"
                    applied += 1

        if applied > 0 and not dry_run:
            self.console.print(f"  [green]{applied} fixes applied to '{item.title}'[/green]")
            return html
        elif applied > 0 and dry_run:
            self.console.print(f"  [yellow]{applied} fixes would be applied to '{item.title}'[/yellow]")

        return None

    def _get_fix_func(self, check_id: str):
        """Map check IDs to fix functions."""
        return {
            "heading-hierarchy": self._fix_heading_hierarchy,
            "table-header-missing-scope": self._fix_table_scope,
            "alt-text-missing": self._fix_alt_text_placeholder,
        }.get(check_id)

    def _fix_heading_hierarchy(self, html: str, issue: AccessibilityIssue) -> str | None:
        """Fix heading level gaps (e.g., h2 -> h4 becomes h2 -> h3)."""
        soup = BeautifulSoup(html, "lxml")
        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])

        prev_level = 0
        changed = False
        for h in headings:
            level = int(h.name[1])
            if prev_level > 0 and level > prev_level + 1:
                new_level = prev_level + 1
                h.name = f"h{new_level}"
                changed = True
                level = new_level
            prev_level = level

        if changed:
            # Extract body content (lxml wraps in html/body)
            body = soup.find("body")
            return "".join(str(child) for child in body.children) if body else str(soup)
        return None

    def _fix_table_scope(self, html: str, issue: AccessibilityIssue) -> str | None:
        """Add scope attribute to table header cells."""
        soup = BeautifulSoup(html, "lxml")
        changed = False

        for th in soup.find_all("th"):
            if not th.has_attr("scope"):
                # Determine if row or column header
                parent_tr = th.find_parent("tr")
                if parent_tr:
                    parent_section = parent_tr.find_parent(["thead", "tbody", "tfoot", "table"])
                    if parent_section and parent_section.name == "thead":
                        th["scope"] = "col"
                    elif parent_tr.find_all("th") and not parent_tr.find_all("td"):
                        th["scope"] = "col"
                    else:
                        # First cell in row is usually a row header
                        first_child = parent_tr.find(["th", "td"])
                        if first_child == th:
                            th["scope"] = "row"
                        else:
                            th["scope"] = "col"
                changed = True

        if changed:
            body = soup.find("body")
            return "".join(str(child) for child in body.children) if body else str(soup)
        return None

    def _fix_alt_text_placeholder(self, html: str, issue: AccessibilityIssue) -> str | None:
        """Add placeholder alt="" to images missing alt attribute (decorative by default)."""
        soup = BeautifulSoup(html, "lxml")
        changed = False

        for img in soup.find_all("img"):
            if not img.has_attr("alt"):
                img["alt"] = ""
                changed = True

        if changed:
            body = soup.find("body")
            return "".join(str(child) for child in body.children) if body else str(soup)
        return None

    def _confirm_fix(self, item_title: str, issue: AccessibilityIssue, old_html: str, new_html: str) -> bool:
        """Show diff and ask for confirmation."""
        if self.auto_approve_all or self.no_confirm:
            return True

        self._show_diff(item_title, issue, old_html, new_html)

        response = self.console.input("[bold]Apply fix? [y/N/all] [/bold]").strip().lower()
        if response == "all":
            self.auto_approve_all = True
            return True
        return response in ("y", "yes")

    def _show_diff(self, item_title: str, issue: AccessibilityIssue, old_html: str, new_html: str) -> None:
        """Display before/after diff."""
        self.console.print(f"\n[bold cyan]Fix:[/bold cyan] {issue.check_id} in '{item_title}'")
        self.console.print(f"  {issue.description}")

        # Show a simplified diff (just the changed parts)
        self.console.print("[red]- Before:[/red]")
        if issue.element_html:
            self.console.print(Syntax(issue.element_html, "html", theme="monokai", line_numbers=False))
        self.console.print("[green]+ After:[/green]")
        # Show a snippet around the fix
        self.console.print(Syntax(new_html[:500] if len(new_html) > 500 else new_html, "html", theme="monokai", line_numbers=False))
