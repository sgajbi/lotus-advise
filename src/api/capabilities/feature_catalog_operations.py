from __future__ import annotations

from src.api.capabilities.degraded_reasons import lifecycle_disabled_reason
from src.api.capabilities.models import FeatureCapability


def build_operational_feature_capabilities(
    *,
    lifecycle_enabled: bool,
) -> list[FeatureCapability]:
    return [
        FeatureCapability(
            key="advisory.proposals.execution_handoff",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled,
            owner_service="ADVISORY",
            description="Advisory execution handoff and execution-state correlation APIs.",
            fallback_mode="NONE",
            degraded_reason=None,
        ),
        FeatureCapability(
            key="advise.observability.advisory_supportability",
            enabled=True,
            operational_ready=lifecycle_enabled,
            owner_service="ADVISORY",
            description=(
                "Source-backed advisory supportability posture for Gateway and Workbench consumers."
            ),
            fallback_mode="NONE",
            degraded_reason=lifecycle_disabled_reason(lifecycle_enabled=lifecycle_enabled),
        ),
    ]


__all__ = ["build_operational_feature_capabilities"]
