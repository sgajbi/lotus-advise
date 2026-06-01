from __future__ import annotations

from src.api.capabilities.dependencies import dependency_rows
from src.api.capabilities.models import (
    AdvisorySupportability,
    FeatureCapability,
    FreshnessBucket,
    SupportabilityReason,
    SupportabilityState,
)
from src.api.observability import record_advisory_supportability


def build_advisory_supportability(
    *,
    readiness: dict[str, object],
    lifecycle_enabled: bool,
    features: list[FeatureCapability],
) -> AdvisorySupportability:
    rows = dependency_rows(readiness)
    dependency_count = len(rows)
    ready_dependency_count = sum(
        1 for dependency in rows if bool(dependency.get("operational_ready"))
    )
    degraded_dependency_count = dependency_count - ready_dependency_count
    enabled_features = [feature for feature in features if feature.enabled]
    ready_feature_count = sum(1 for feature in enabled_features if feature.operational_ready)

    if not lifecycle_enabled:
        state: SupportabilityState = "unsupported"
        reason: SupportabilityReason = "lifecycle_disabled"
        freshness_bucket: FreshnessBucket = "unknown"
    elif degraded_dependency_count > 0 or ready_feature_count < len(enabled_features):
        state = "degraded"
        reason = "dependency_degraded"
        freshness_bucket = "unknown"
    else:
        state = "ready"
        reason = "advisory_ready"
        freshness_bucket = "current"

    supportability = AdvisorySupportability(
        state=state,
        reason=reason,
        freshness_bucket=freshness_bucket,
        dependency_count=dependency_count,
        ready_dependency_count=ready_dependency_count,
        degraded_dependency_count=degraded_dependency_count,
        enabled_feature_count=len(enabled_features),
        ready_feature_count=ready_feature_count,
    )
    record_advisory_supportability(
        state=supportability.state,
        reason=supportability.reason,
        freshness_bucket=supportability.freshness_bucket,
    )
    return supportability


__all__ = ["build_advisory_supportability"]
