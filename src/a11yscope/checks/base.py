"""Abstract base class for accessibility checks."""
from abc import ABC, abstractmethod
from a11yscope.models import AccessibilityIssue


class AccessibilityCheck(ABC):
    """Base class for all accessibility checks."""

    check_id: str = ""
    title: str = ""
    description: str = ""
    wcag_criterion: str = ""

    @abstractmethod
    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        """Run this check against HTML content. Returns list of issues found."""
        ...

    def _make_issue(self, description: str, element_html: str | None = None,
                    severity=None, auto_fixable: bool = False,
                    ai_fixable: bool = False, line_number: int | None = None) -> AccessibilityIssue:
        from a11yscope.models import Severity
        return AccessibilityIssue(
            check_id=self.check_id,
            title=self.title,
            description=description,
            severity=severity or Severity.SERIOUS,
            wcag_criterion=self.wcag_criterion,
            element_html=element_html,
            line_number=line_number,
            auto_fixable=auto_fixable,
            ai_fixable=ai_fixable,
        )
