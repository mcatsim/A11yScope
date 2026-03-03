"""Standards mapping for WCAG 2.1/2.2, Section 508, and VPAT reporting."""

from a11yscope.standards.wcag21 import WCAG_CRITERIA, WCAGCriterion
from a11yscope.standards.section508 import SECTION_508_PROVISIONS, Section508Provision
from a11yscope.standards.mapping import (
    CHECK_STANDARDS_MAP,
    StandardsMapping,
    get_standards_for_check,
)
from a11yscope.standards.vpat import VPATReport, VPATRow, build_vpat
from a11yscope.standards.updater import (
    check_for_updates,
    apply_updates,
    get_effective_standards,
)

__all__ = [
    "WCAG_CRITERIA",
    "WCAGCriterion",
    "SECTION_508_PROVISIONS",
    "Section508Provision",
    "CHECK_STANDARDS_MAP",
    "StandardsMapping",
    "get_standards_for_check",
    "VPATReport",
    "VPATRow",
    "build_vpat",
    "check_for_updates",
    "apply_updates",
    "get_effective_standards",
]
