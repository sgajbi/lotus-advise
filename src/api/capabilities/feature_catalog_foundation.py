from __future__ import annotations

from src.api.capabilities.degraded_reasons import (
    LOTUS_AI_DEPENDENCY_UNAVAILABLE,
    LOTUS_CORE_DEPENDENCY_UNAVAILABLE,
    LOTUS_REPORT_DEPENDENCY_UNAVAILABLE,
    LOTUS_RISK_DEPENDENCY_UNAVAILABLE,
    dependency_unavailable_reason,
    gated_dependency_unavailable_reason,
)
from src.api.capabilities.dependencies import CapabilityDependencyStatus
from src.api.capabilities.models import FeatureCapability
from src.integrations.lotus_core import lotus_core_fallback_mode


def build_foundational_feature_capabilities(
    *,
    lifecycle_enabled: bool,
    async_enabled: bool,
    ai_rationale_enabled: bool,
    dependency_status: CapabilityDependencyStatus,
) -> list[FeatureCapability]:
    return [
        FeatureCapability(
            key="advisory.proposals.simulation",
            enabled=True,
            operational_ready=dependency_status.lotus_core_ready,
            owner_service="LOTUS_CORE",
            description=(
                "Canonical advisory proposal simulation through lotus-core; "
                "lotus-advise remains the workflow and API owner."
            ),
            fallback_mode=lotus_core_fallback_mode(),
            degraded_reason=dependency_unavailable_reason(
                ready=dependency_status.lotus_core_ready,
                reason=LOTUS_CORE_DEPENDENCY_UNAVAILABLE,
            ),
        ),
        FeatureCapability(
            key="advisory.proposals.lifecycle",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled,
            owner_service="ADVISORY",
            description="Advisory proposal lifecycle APIs.",
            fallback_mode="NONE",
            degraded_reason=None,
        ),
        FeatureCapability(
            key="advisory.proposals.async_operations",
            enabled=async_enabled,
            operational_ready=async_enabled,
            owner_service="ADVISORY",
            description="Async advisory proposal operations.",
            fallback_mode="NONE",
            degraded_reason=None,
        ),
        FeatureCapability(
            key="advisory.workspaces.stateful",
            enabled=True,
            operational_ready=dependency_status.lotus_core_ready,
            owner_service="ADVISORY",
            description=(
                "Stateful advisory workspace evaluation through Lotus Core context resolution."
            ),
            fallback_mode=lotus_core_fallback_mode(),
            degraded_reason=dependency_unavailable_reason(
                ready=dependency_status.lotus_core_ready,
                reason=LOTUS_CORE_DEPENDENCY_UNAVAILABLE,
            ),
        ),
        FeatureCapability(
            key="advisory.workspaces.ai_rationale",
            enabled=ai_rationale_enabled,
            operational_ready=ai_rationale_enabled and dependency_status.lotus_ai_ready,
            owner_service="ADVISORY",
            description="Evidence-grounded advisory workspace rationale through Lotus AI.",
            fallback_mode="NONE",
            degraded_reason=gated_dependency_unavailable_reason(
                enabled=ai_rationale_enabled,
                ready=dependency_status.lotus_ai_ready,
                reason=LOTUS_AI_DEPENDENCY_UNAVAILABLE,
            ),
        ),
        FeatureCapability(
            key="advisory.proposals.risk_lens",
            enabled=True,
            operational_ready=dependency_status.lotus_risk_ready,
            owner_service="LOTUS_RISK",
            description="Proposal before/after concentration risk lens through lotus-risk.",
            fallback_mode="LOCAL_RISK_FALLBACK",
            degraded_reason=dependency_unavailable_reason(
                ready=dependency_status.lotus_risk_ready,
                reason=LOTUS_RISK_DEPENDENCY_UNAVAILABLE,
            ),
        ),
        FeatureCapability(
            key="advisory.proposals.reporting",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and dependency_status.lotus_report_ready,
            owner_service="LOTUS_REPORT",
            description=(
                "Advisory proposal report-request integration boundary through lotus-report."
            ),
            fallback_mode="NONE",
            degraded_reason=gated_dependency_unavailable_reason(
                enabled=lifecycle_enabled,
                ready=dependency_status.lotus_report_ready,
                reason=LOTUS_REPORT_DEPENDENCY_UNAVAILABLE,
            ),
        ),
    ]


__all__ = ["build_foundational_feature_capabilities"]
