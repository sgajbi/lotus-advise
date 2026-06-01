from __future__ import annotations

ADVISORY_LIFECYCLE_DISABLED = "ADVISORY_LIFECYCLE_DISABLED"
LOTUS_AI_DEPENDENCY_UNAVAILABLE = "LOTUS_AI_DEPENDENCY_UNAVAILABLE"
LOTUS_CORE_DEPENDENCY_UNAVAILABLE = "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"
LOTUS_REPORT_DEPENDENCY_UNAVAILABLE = "LOTUS_REPORT_DEPENDENCY_UNAVAILABLE"
LOTUS_RISK_DEPENDENCY_UNAVAILABLE = "LOTUS_RISK_DEPENDENCY_UNAVAILABLE"
RFC0028_PROOF_DEPENDENCY_UNAVAILABLE = "RFC0028_PROOF_DEPENDENCY_UNAVAILABLE"


def dependency_unavailable_reason(*, ready: bool, reason: str) -> str | None:
    if ready:
        return None
    return reason


def gated_dependency_unavailable_reason(
    *,
    enabled: bool,
    ready: bool,
    reason: str,
) -> str | None:
    if not enabled or ready:
        return None
    return reason


def lifecycle_disabled_reason(*, lifecycle_enabled: bool) -> str | None:
    if lifecycle_enabled:
        return None
    return ADVISORY_LIFECYCLE_DISABLED


__all__ = [
    "ADVISORY_LIFECYCLE_DISABLED",
    "LOTUS_AI_DEPENDENCY_UNAVAILABLE",
    "LOTUS_CORE_DEPENDENCY_UNAVAILABLE",
    "LOTUS_REPORT_DEPENDENCY_UNAVAILABLE",
    "LOTUS_RISK_DEPENDENCY_UNAVAILABLE",
    "RFC0028_PROOF_DEPENDENCY_UNAVAILABLE",
    "dependency_unavailable_reason",
    "gated_dependency_unavailable_reason",
    "lifecycle_disabled_reason",
]
