"""Standards mapping for WCAG 2.1/2.2, Section 508, and VPAT reporting."""

from accessiflow.standards.wcag21 import WCAG_CRITERIA, WCAGCriterion
from accessiflow.standards.section508 import SECTION_508_PROVISIONS, Section508Provision
from accessiflow.standards.mapping import (
    CHECK_STANDARDS_MAP,
    StandardsMapping,
    get_standards_for_check,
)
from accessiflow.standards.vpat import VPATReport, VPATRow, build_vpat
from accessiflow.standards.updater import (
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
