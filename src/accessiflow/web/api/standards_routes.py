"""Standards management API endpoints.

Provides REST endpoints for:
- Viewing current standards data and versions
- Checking for updates (WCAG 2.2, etc.)
- Applying updates to local cache
- Adding custom criteria and mappings
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from accessiflow.standards.updater import (
    add_custom_criterion,
    add_custom_mapping,
    apply_updates,
    check_for_updates,
    get_effective_standards,
    load_versions,
    reset_cache,
    DEFAULT_CACHE_DIR,
)

router = APIRouter(tags=["standards"])


@router.get("/standards")
async def get_standards():
    """Get the effective (merged) standards data with stats."""
    return get_effective_standards()


@router.get("/standards/versions")
async def get_versions():
    """Get version tracking info for all standards sets."""
    versions = load_versions()
    if not versions:
        return {"versions": [], "message": "No version data. Run a check first."}
    return {
        "versions": [
            {
                "standard": v.standard,
                "version": v.version,
                "last_checked": v.last_checked,
                "last_updated": v.last_updated,
                "criteria_count": v.criteria_count,
                "source_url": v.source_url,
            }
            for v in versions
        ]
    }


@router.post("/standards/check")
async def check_standards_updates():
    """Self-check: compare local standards data against latest available.

    Checks for:
    - Missing WCAG 2.1 criteria (data integrity)
    - New WCAG 2.2 Level A/AA criteria not yet in cache
    - Section 508 provision completeness
    - W3C site reachability
    """
    result = await check_for_updates()
    return {
        "checked_at": result.checked_at,
        "updates_available": result.updates_available,
        "current_versions": [
            {
                "standard": v.standard,
                "version": v.version,
                "criteria_count": v.criteria_count,
                "source_url": v.source_url,
            }
            for v in result.current_versions
        ],
        "messages": result.messages,
        "new_criteria": result.new_criteria,
    }


@router.post("/standards/update")
async def apply_standards_updates(include_wcag22: bool = True):
    """Download and merge available standards updates.

    Args:
        include_wcag22: Whether to include WCAG 2.2 new A/AA criteria (default: True)
    """
    cache = await apply_updates(include_wcag22=include_wcag22)
    stats = get_effective_standards().get("stats", {})
    return {
        "ok": True,
        "message": "Standards updated successfully.",
        "stats": stats,
    }


@router.post("/standards/reset")
async def reset_standards_cache():
    """Reset standards cache to built-in defaults (WCAG 2.1 + Section 508)."""
    reset_cache()
    stats = get_effective_standards().get("stats", {})
    return {
        "ok": True,
        "message": "Standards cache reset to built-in defaults.",
        "stats": stats,
    }


@router.post("/standards/custom/criterion")
async def add_criterion(
    criterion_id: str,
    name: str,
    level: str,
    principle: str,
    url: str = "",
    description: str = "",
):
    """Add a custom criterion to the local standards cache.

    Useful for organization-specific requirements or tracking newer drafts.
    """
    add_custom_criterion(
        criterion_id=criterion_id,
        name=name,
        level=level,
        principle=principle,
        url=url,
        description=description,
    )
    return {
        "ok": True,
        "message": f"Custom criterion '{criterion_id}' added.",
    }


@router.post("/standards/custom/mapping")
async def add_mapping(
    check_id: str,
    wcag_criteria: list[str],
    section_508_provisions: list[str] | None = None,
    best_practice_urls: list[str] | None = None,
):
    """Add or extend a check-to-standards mapping."""
    add_custom_mapping(
        check_id=check_id,
        wcag_criteria=wcag_criteria,
        section_508_provisions=section_508_provisions,
        best_practice_urls=best_practice_urls,
    )
    return {
        "ok": True,
        "message": f"Mapping for check '{check_id}' updated.",
    }
