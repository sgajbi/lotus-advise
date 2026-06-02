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
from src.api.capabilities.models import WorkflowCapability


def build_foundational_workflow_capabilities(
    *,
    lifecycle_enabled: bool,
    ai_rationale_enabled: bool,
    dependency_status: CapabilityDependencyStatus,
) -> list[WorkflowCapability]:
    return [
        WorkflowCapability(
            workflow_key="advisory_proposal_simulation",
            enabled=True,
            operational_ready=dependency_status.lotus_core_ready,
            required_features=["advisory.proposals.simulation"],
            dependency_keys=["lotus_core"],
            degraded_reason=dependency_unavailable_reason(
                ready=dependency_status.lotus_core_ready,
                reason=LOTUS_CORE_DEPENDENCY_UNAVAILABLE,
            ),
        ),
        WorkflowCapability(
            workflow_key="advisory_proposal_lifecycle",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled,
            required_features=["advisory.proposals.lifecycle"],
            dependency_keys=[],
            degraded_reason=None,
        ),
        WorkflowCapability(
            workflow_key="advisory_workspace_stateful",
            enabled=True,
            operational_ready=dependency_status.lotus_core_ready,
            required_features=["advisory.workspaces.stateful"],
            dependency_keys=["lotus_core"],
            degraded_reason=dependency_unavailable_reason(
                ready=dependency_status.lotus_core_ready,
                reason=LOTUS_CORE_DEPENDENCY_UNAVAILABLE,
            ),
        ),
        WorkflowCapability(
            workflow_key="advisory_workspace_ai_rationale",
            enabled=ai_rationale_enabled,
            operational_ready=ai_rationale_enabled and dependency_status.lotus_ai_ready,
            required_features=["advisory.workspaces.ai_rationale"],
            dependency_keys=["lotus_ai"],
            degraded_reason=gated_dependency_unavailable_reason(
                enabled=ai_rationale_enabled,
                ready=dependency_status.lotus_ai_ready,
                reason=LOTUS_AI_DEPENDENCY_UNAVAILABLE,
            ),
        ),
        WorkflowCapability(
            workflow_key="advisory_proposal_risk_lens",
            enabled=True,
            operational_ready=dependency_status.lotus_risk_ready,
            required_features=["advisory.proposals.risk_lens"],
            dependency_keys=["lotus_risk"],
            degraded_reason=dependency_unavailable_reason(
                ready=dependency_status.lotus_risk_ready,
                reason=LOTUS_RISK_DEPENDENCY_UNAVAILABLE,
            ),
        ),
        WorkflowCapability(
            workflow_key="advisory_proposal_reporting",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and dependency_status.lotus_report_ready,
            required_features=["advisory.proposals.reporting"],
            dependency_keys=["lotus_report"],
            degraded_reason=gated_dependency_unavailable_reason(
                enabled=lifecycle_enabled,
                ready=dependency_status.lotus_report_ready,
                reason=LOTUS_REPORT_DEPENDENCY_UNAVAILABLE,
            ),
        ),
    ]


__all__ = ["build_foundational_workflow_capabilities"]
