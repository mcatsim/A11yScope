"""Pluggable check registry."""
from a11yscope.checks.base import AccessibilityCheck

_registry: list[type[AccessibilityCheck]] = []


def register_check(cls: type[AccessibilityCheck]) -> type[AccessibilityCheck]:
    """Decorator to register a check class."""
    _registry.append(cls)
    return cls


def get_all_checks() -> list[AccessibilityCheck]:
    """Return instances of all registered checks."""
    return [cls() for cls in _registry]


def get_check_by_id(check_id: str) -> AccessibilityCheck | None:
    for cls in _registry:
        if cls.check_id == check_id:
            return cls()
    return None
