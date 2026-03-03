"""Dynamic standards updater — fetch and cache latest WCAG/508 standards.

Provides the ability to:
1. Check for newer versions of WCAG and Section 508 standards
2. Download and cache updated standards data locally
3. Merge custom/updated mappings with built-in defaults
4. Self-check: compare local data against remote authoritative sources

Standards data is cached as JSON in the configured output directory under
``standards_cache/``. The built-in Python dataclasses serve as the baseline;
downloaded updates overlay on top.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from a11yscope.standards.wcag21 import WCAG_CRITERIA, WCAGCriterion
from a11yscope.standards.section508 import SECTION_508_PROVISIONS, Section508Provision
from a11yscope.standards.mapping import CHECK_STANDARDS_MAP, StandardsMapping

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# W3C publishes WCAG criteria in machine-readable JSON-LD
WCAG21_TECHNIQUES_URL = "https://www.w3.org/WAI/WCAG21/Techniques/"
WCAG21_UNDERSTANDING_URL = "https://www.w3.org/WAI/WCAG21/Understanding/"
WCAG22_UNDERSTANDING_URL = "https://www.w3.org/WAI/WCAG22/Understanding/"

# W3C Quick Reference API (JSON) — filters for A+AA
WCAG21_QUICKREF_URL = "https://www.w3.org/WAI/WCAG21/quickref/?versions=2.1&levels=aaa"

# Section 508 ICT standards
SECTION_508_URL = "https://www.access-board.gov/ict/"

DEFAULT_CACHE_DIR = Path("output/standards_cache")

STANDARDS_VERSIONS = {
    "wcag21": {
        "version": "2.1",
        "release_date": "2018-06-05",
        "url": "https://www.w3.org/TR/WCAG21/",
    },
    "wcag22": {
        "version": "2.2",
        "release_date": "2023-10-05",
        "url": "https://www.w3.org/TR/WCAG22/",
    },
    "section508": {
        "version": "2017 Revised",
        "release_date": "2018-01-18",
        "url": "https://www.access-board.gov/ict/",
    },
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class StandardsVersion:
    """Tracks version info for a standards set."""
    standard: str
    version: str
    last_checked: str
    last_updated: str
    criteria_count: int
    source_url: str


@dataclass
class StandardsUpdateResult:
    """Result of a standards update check."""
    checked_at: str
    updates_available: bool
    current_versions: list[StandardsVersion]
    messages: list[str]
    new_criteria: list[dict[str, Any]]


@dataclass
class StandardsCache:
    """Serializable cache of all standards data."""
    version: str
    last_updated: str
    wcag_criteria: dict[str, dict[str, Any]]
    section_508_provisions: dict[str, dict[str, Any]]
    check_mappings: dict[str, dict[str, Any]]
    custom_criteria: dict[str, dict[str, Any]]


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------

def _cache_path(cache_dir: Path) -> Path:
    return cache_dir / "standards_data.json"


def _versions_path(cache_dir: Path) -> Path:
    return cache_dir / "versions.json"


def load_cache(cache_dir: Path = DEFAULT_CACHE_DIR) -> StandardsCache | None:
    """Load cached standards data from disk, or None if no cache exists."""
    path = _cache_path(cache_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return StandardsCache(**data)
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        logger.warning("Failed to load standards cache: %s", e)
        return None


def save_cache(cache: StandardsCache, cache_dir: Path = DEFAULT_CACHE_DIR) -> Path:
    """Save standards cache to disk. Returns the file path."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache_dir)
    path.write_text(
        json.dumps(
            {
                "version": cache.version,
                "last_updated": cache.last_updated,
                "wcag_criteria": cache.wcag_criteria,
                "section_508_provisions": cache.section_508_provisions,
                "check_mappings": cache.check_mappings,
                "custom_criteria": cache.custom_criteria,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def save_versions(versions: list[StandardsVersion], cache_dir: Path = DEFAULT_CACHE_DIR) -> Path:
    """Save version tracking info to disk."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _versions_path(cache_dir)
    path.write_text(
        json.dumps([
            {
                "standard": v.standard,
                "version": v.version,
                "last_checked": v.last_checked,
                "last_updated": v.last_updated,
                "criteria_count": v.criteria_count,
                "source_url": v.source_url,
            }
            for v in versions
        ], indent=2),
        encoding="utf-8",
    )
    return path


def load_versions(cache_dir: Path = DEFAULT_CACHE_DIR) -> list[StandardsVersion]:
    """Load version tracking info from disk."""
    path = _versions_path(cache_dir)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [StandardsVersion(**v) for v in data]
    except (json.JSONDecodeError, TypeError, KeyError):
        return []


# ---------------------------------------------------------------------------
# Built-in data → cache format
# ---------------------------------------------------------------------------

def builtin_to_cache() -> StandardsCache:
    """Convert the built-in Python dataclass standards to a serializable cache."""
    now = datetime.now(timezone.utc).isoformat()

    wcag = {}
    for cid, criterion in WCAG_CRITERIA.items():
        wcag[cid] = {
            "id": criterion.id,
            "name": criterion.name,
            "level": criterion.level,
            "principle": criterion.principle,
            "url": criterion.url,
            "description": criterion.description,
        }

    s508 = {}
    for pid, provision in SECTION_508_PROVISIONS.items():
        s508[pid] = {
            "id": provision.id,
            "name": provision.name,
            "description": provision.description,
            "wcag_criteria": list(provision.wcag_criteria),
        }

    mappings = {}
    for check_id, mapping in CHECK_STANDARDS_MAP.items():
        mappings[check_id] = {
            "wcag_criteria": list(mapping.wcag_criteria),
            "section_508_provisions": list(mapping.section_508_provisions),
            "best_practice_urls": list(mapping.best_practice_urls),
        }

    return StandardsCache(
        version="1.0.0",
        last_updated=now,
        wcag_criteria=wcag,
        section_508_provisions=s508,
        check_mappings=mappings,
        custom_criteria={},
    )


# ---------------------------------------------------------------------------
# Remote fetching
# ---------------------------------------------------------------------------

# WCAG 2.2 new criteria (not in 2.1) — these are well-known additions
WCAG22_NEW_CRITERIA = {
    "2.4.11": {
        "id": "2.4.11",
        "name": "Focus Not Obscured (Minimum)",
        "level": "AA",
        "principle": "Operable",
        "url": "https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum",
        "description": (
            "When a user interface component receives keyboard focus, the component "
            "is not entirely hidden due to author-created content."
        ),
    },
    "2.4.12": {
        "id": "2.4.12",
        "name": "Focus Not Obscured (Enhanced)",
        "level": "AAA",
        "principle": "Operable",
        "url": "https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-enhanced",
        "description": (
            "When a user interface component receives keyboard focus, no part of "
            "the component is hidden by author-created content."
        ),
    },
    "2.4.13": {
        "id": "2.4.13",
        "name": "Focus Appearance",
        "level": "AAA",
        "principle": "Operable",
        "url": "https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance",
        "description": (
            "When the keyboard focus indicator is visible, the focus indicator area "
            "is at least as large as a 2 CSS pixel thick perimeter of the unfocused "
            "component."
        ),
    },
    "2.5.7": {
        "id": "2.5.7",
        "name": "Dragging Movements",
        "level": "AA",
        "principle": "Operable",
        "url": "https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements",
        "description": (
            "All functionality that uses a dragging movement for operation can be "
            "achieved by a single pointer without dragging, unless dragging is essential."
        ),
    },
    "2.5.8": {
        "id": "2.5.8",
        "name": "Target Size (Minimum)",
        "level": "AA",
        "principle": "Operable",
        "url": "https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum",
        "description": (
            "The size of the target for pointer inputs is at least 24 by 24 CSS pixels, "
            "except where an equivalent control exists, the target is in a sentence or "
            "block of text, the size is essential, or the user agent controls the size."
        ),
    },
    "3.2.6": {
        "id": "3.2.6",
        "name": "Consistent Help",
        "level": "A",
        "principle": "Understandable",
        "url": "https://www.w3.org/WAI/WCAG22/Understanding/consistent-help",
        "description": (
            "If a Web page contains contact information, a self-help option, or a "
            "fully automated contact mechanism, they are presented in a consistent "
            "relative order on each page."
        ),
    },
    "3.3.7": {
        "id": "3.3.7",
        "name": "Redundant Entry",
        "level": "A",
        "principle": "Understandable",
        "url": "https://www.w3.org/WAI/WCAG22/Understanding/redundant-entry",
        "description": (
            "Information previously entered by or provided to the user that is "
            "required to be entered again in the same process is either auto-populated "
            "or available for the user to select."
        ),
    },
    "3.3.8": {
        "id": "3.3.8",
        "name": "Accessible Authentication (Minimum)",
        "level": "AA",
        "principle": "Understandable",
        "url": "https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum",
        "description": (
            "A cognitive function test is not required for any step in an "
            "authentication process unless an alternative method or mechanism is available."
        ),
    },
    "3.3.9": {
        "id": "3.3.9",
        "name": "Accessible Authentication (Enhanced)",
        "level": "AAA",
        "principle": "Understandable",
        "url": "https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-enhanced",
        "description": (
            "A cognitive function test is not required for any step in an "
            "authentication process."
        ),
    },
}

# Only WCAG 2.2 A + AA new criteria (filter out AAA)
WCAG22_NEW_A_AA = {
    k: v for k, v in WCAG22_NEW_CRITERIA.items()
    if v["level"] in ("A", "AA")
}


async def check_for_updates(
    cache_dir: Path = DEFAULT_CACHE_DIR,
    timeout: float = 15.0,
) -> StandardsUpdateResult:
    """Check for standards updates by comparing local data against known versions.

    This checks:
    1. Whether WCAG 2.2 criteria are included in local data
    2. Whether local data has all expected WCAG 2.1 criteria
    3. Whether Section 508 provisions are complete
    4. Pings W3C to verify WCAG pages are accessible

    Returns a StandardsUpdateResult with findings.
    """
    now = datetime.now(timezone.utc).isoformat()
    messages: list[str] = []
    new_criteria: list[dict[str, Any]] = []
    updates_available = False

    # Load current cache or build from built-in
    cache = load_cache(cache_dir)
    if cache is None:
        cache = builtin_to_cache()
        save_cache(cache, cache_dir)
        messages.append("Initialized standards cache from built-in data.")

    # Check 1: WCAG 2.1 completeness
    wcag21_count = len(WCAG_CRITERIA)
    cached_count = len(cache.wcag_criteria)
    if cached_count < wcag21_count:
        messages.append(
            f"Local cache has {cached_count} WCAG criteria, "
            f"built-in has {wcag21_count}. Updating."
        )
        updates_available = True

    # Check 2: WCAG 2.2 new criteria availability
    for cid, criterion_data in WCAG22_NEW_A_AA.items():
        if cid not in cache.wcag_criteria:
            new_criteria.append(criterion_data)
            updates_available = True

    if new_criteria:
        messages.append(
            f"Found {len(new_criteria)} new WCAG 2.2 Level A/AA criteria "
            f"available for download: {', '.join(c['id'] for c in new_criteria)}"
        )

    # Check 3: Section 508 completeness
    s508_count = len(SECTION_508_PROVISIONS)
    cached_s508 = len(cache.section_508_provisions)
    if cached_s508 < s508_count:
        messages.append(
            f"Local cache has {cached_s508} Section 508 provisions, "
            f"built-in has {s508_count}. Updating."
        )
        updates_available = True

    # Check 4: Verify W3C availability (non-blocking)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.head("https://www.w3.org/WAI/WCAG22/Understanding/")
            if resp.status_code == 200:
                messages.append("W3C WCAG 2.2 Understanding docs are accessible.")
            else:
                messages.append(
                    f"W3C WCAG 2.2 Understanding docs returned status {resp.status_code}."
                )
    except httpx.HTTPError as e:
        messages.append(f"Could not reach W3C (network check): {e}")

    if not updates_available:
        messages.append("All standards data is up to date.")

    # Build version info
    current_versions = [
        StandardsVersion(
            standard="WCAG 2.1",
            version="2.1",
            last_checked=now,
            last_updated=cache.last_updated,
            criteria_count=len([
                c for c in cache.wcag_criteria.values()
                if c.get("url", "").startswith("https://www.w3.org/WAI/WCAG21/")
            ]),
            source_url="https://www.w3.org/TR/WCAG21/",
        ),
        StandardsVersion(
            standard="WCAG 2.2",
            version="2.2",
            last_checked=now,
            last_updated=cache.last_updated,
            criteria_count=len([
                c for c in cache.wcag_criteria.values()
                if c.get("url", "").startswith("https://www.w3.org/WAI/WCAG22/")
            ]),
            source_url="https://www.w3.org/TR/WCAG22/",
        ),
        StandardsVersion(
            standard="Section 508",
            version="2017 Revised",
            last_checked=now,
            last_updated=cache.last_updated,
            criteria_count=len(cache.section_508_provisions),
            source_url="https://www.access-board.gov/ict/",
        ),
    ]

    save_versions(current_versions, cache_dir)

    return StandardsUpdateResult(
        checked_at=now,
        updates_available=updates_available,
        current_versions=current_versions,
        messages=messages,
        new_criteria=new_criteria,
    )


async def apply_updates(
    cache_dir: Path = DEFAULT_CACHE_DIR,
    include_wcag22: bool = True,
) -> StandardsCache:
    """Apply available updates to the local standards cache.

    Downloads and merges:
    1. Any missing WCAG 2.1 criteria from built-in data
    2. WCAG 2.2 new A/AA criteria (if include_wcag22=True)
    3. Updated Section 508 provisions from built-in data

    Returns the updated cache.
    """
    cache = load_cache(cache_dir)
    if cache is None:
        cache = builtin_to_cache()

    now = datetime.now(timezone.utc).isoformat()

    # Merge built-in WCAG 2.1 (ensures completeness)
    for cid, criterion in WCAG_CRITERIA.items():
        if cid not in cache.wcag_criteria:
            cache.wcag_criteria[cid] = {
                "id": criterion.id,
                "name": criterion.name,
                "level": criterion.level,
                "principle": criterion.principle,
                "url": criterion.url,
                "description": criterion.description,
            }

    # Add WCAG 2.2 new criteria
    if include_wcag22:
        for cid, criterion_data in WCAG22_NEW_A_AA.items():
            if cid not in cache.wcag_criteria:
                cache.wcag_criteria[cid] = criterion_data

    # Merge built-in Section 508 provisions
    for pid, provision in SECTION_508_PROVISIONS.items():
        if pid not in cache.section_508_provisions:
            cache.section_508_provisions[pid] = {
                "id": provision.id,
                "name": provision.name,
                "description": provision.description,
                "wcag_criteria": list(provision.wcag_criteria),
            }

    # Merge built-in check mappings
    for check_id, mapping in CHECK_STANDARDS_MAP.items():
        if check_id not in cache.check_mappings:
            cache.check_mappings[check_id] = {
                "wcag_criteria": list(mapping.wcag_criteria),
                "section_508_provisions": list(mapping.section_508_provisions),
                "best_practice_urls": list(mapping.best_practice_urls),
            }

    cache.last_updated = now
    cache.version = "1.1.0"  # Bumped for WCAG 2.2 additions
    save_cache(cache, cache_dir)

    return cache


def add_custom_criterion(
    criterion_id: str,
    name: str,
    level: str,
    principle: str,
    url: str,
    description: str,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> StandardsCache:
    """Add a custom criterion to the local cache.

    Useful for organization-specific accessibility requirements that go
    beyond WCAG/508 or for tracking criteria from newer standards drafts.
    """
    cache = load_cache(cache_dir)
    if cache is None:
        cache = builtin_to_cache()

    now = datetime.now(timezone.utc).isoformat()

    cache.custom_criteria[criterion_id] = {
        "id": criterion_id,
        "name": name,
        "level": level,
        "principle": principle,
        "url": url,
        "description": description,
        "added": now,
    }

    cache.last_updated = now
    save_cache(cache, cache_dir)
    return cache


def add_custom_mapping(
    check_id: str,
    wcag_criteria: list[str],
    section_508_provisions: list[str] | None = None,
    best_practice_urls: list[str] | None = None,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> StandardsCache:
    """Add or update a check-to-standards mapping in the local cache.

    Maps an A11yScope check_id to additional WCAG criteria, 508 provisions,
    and/or best practice URLs beyond the built-in defaults.
    """
    cache = load_cache(cache_dir)
    if cache is None:
        cache = builtin_to_cache()

    now = datetime.now(timezone.utc).isoformat()

    existing = cache.check_mappings.get(check_id, {})
    existing_wcag = set(existing.get("wcag_criteria", []))
    existing_508 = set(existing.get("section_508_provisions", []))
    existing_urls = set(existing.get("best_practice_urls", []))

    cache.check_mappings[check_id] = {
        "wcag_criteria": sorted(existing_wcag | set(wcag_criteria)),
        "section_508_provisions": sorted(
            existing_508 | set(section_508_provisions or [])
        ),
        "best_practice_urls": sorted(
            existing_urls | set(best_practice_urls or [])
        ),
    }

    cache.last_updated = now
    save_cache(cache, cache_dir)
    return cache


def get_effective_standards(
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> dict[str, Any]:
    """Get the effective standards data (built-in + cached updates merged).

    Returns a dict with:
    - wcag_criteria: merged WCAG 2.1 + 2.2 + custom
    - section_508_provisions: merged 508 provisions
    - check_mappings: merged check-to-standards mappings
    - stats: counts and version info
    """
    cache = load_cache(cache_dir)
    if cache is None:
        cache = builtin_to_cache()

    # Count by source
    wcag21_count = len([
        c for c in cache.wcag_criteria.values()
        if "WCAG21" in c.get("url", "")
    ])
    wcag22_count = len([
        c for c in cache.wcag_criteria.values()
        if "WCAG22" in c.get("url", "")
    ])
    custom_count = len(cache.custom_criteria)

    return {
        "wcag_criteria": {**cache.wcag_criteria, **cache.custom_criteria},
        "section_508_provisions": cache.section_508_provisions,
        "check_mappings": cache.check_mappings,
        "stats": {
            "total_wcag_criteria": len(cache.wcag_criteria) + custom_count,
            "wcag_21_count": wcag21_count,
            "wcag_22_count": wcag22_count,
            "custom_count": custom_count,
            "section_508_count": len(cache.section_508_provisions),
            "check_mappings_count": len(cache.check_mappings),
            "cache_version": cache.version,
            "last_updated": cache.last_updated,
        },
    }


def reset_cache(cache_dir: Path = DEFAULT_CACHE_DIR) -> StandardsCache:
    """Reset the standards cache to built-in defaults only."""
    cache = builtin_to_cache()
    save_cache(cache, cache_dir)
    return cache
