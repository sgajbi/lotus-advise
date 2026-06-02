from __future__ import annotations

from src.api.capabilities.degraded_reasons import (
    LOTUS_AI_DEPENDENCY_UNAVAILABLE,
    LOTUS_REPORT_DEPENDENCY_UNAVAILABLE,
    gated_dependency_unavailable_reason,
    lifecycle_disabled_reason,
)
from src.api.capabilities.dependencies import (
    CapabilityDependencyStatus,
    bank_demo_proof_dependency_keys,
)
from src.api.capabilities.models import WorkflowCapability


def build_evidence_product_workflow_capabilities(
    *,
    lifecycle_enabled: bool,
    dependency_status: CapabilityDependencyStatus,
) -> list[WorkflowCapability]:
    return [
        WorkflowCapability(
            workflow_key="advisory_proposal_reviewed_narrative_evidence",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled,
            required_features=[
                "advisory.proposals.lifecycle",
                "advisory.proposals.reviewed_narrative_evidence",
            ],
            dependency_keys=[],
            degraded_reason=lifecycle_disabled_reason(lifecycle_enabled=lifecycle_enabled),
        ),
        WorkflowCapability(
            workflow_key="advisory_proposal_memo_evidence_pack",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and dependency_status.lotus_report_ready,
            required_features=[
                "advisory.proposals.lifecycle",
                "advisory.proposals.memo_evidence_pack",
                "advisory.proposals.reporting",
            ],
            dependency_keys=["lotus_report"],
            degraded_reason=gated_dependency_unavailable_reason(
                enabled=lifecycle_enabled,
                ready=dependency_status.lotus_report_ready,
                reason=LOTUS_REPORT_DEPENDENCY_UNAVAILABLE,
            ),
        ),
        WorkflowCapability(
            workflow_key="advisory_policy_pack_catalog",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled,
            required_features=[
                "advisory.proposals.lifecycle",
                "advisory.policy_pack_catalog",
            ],
            dependency_keys=[],
            degraded_reason=lifecycle_disabled_reason(lifecycle_enabled=lifecycle_enabled),
        ),
        WorkflowCapability(
            workflow_key="advisory_policy_evaluation",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and dependency_status.lotus_report_ready,
            required_features=[
                "advisory.proposals.lifecycle",
                "advisory.policy_pack_catalog",
                "advisory.proposals.policy_evaluation",
                "advisory.proposals.reporting",
            ],
            dependency_keys=["lotus_report"],
            degraded_reason=gated_dependency_unavailable_reason(
                enabled=lifecycle_enabled,
                ready=dependency_status.lotus_report_ready,
                reason=LOTUS_REPORT_DEPENDENCY_UNAVAILABLE,
            ),
        ),
        WorkflowCapability(
            workflow_key="advisor_cockpit_operating_workflow",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled,
            required_features=[
                "advisory.proposals.lifecycle",
                "advisory.policy_pack_catalog",
                "advisory.proposals.policy_evaluation",
                "advisory.proposals.memo_evidence_pack",
                "advisory.advisor_cockpit",
            ],
            dependency_keys=[],
            degraded_reason=lifecycle_disabled_reason(lifecycle_enabled=lifecycle_enabled),
        ),
        WorkflowCapability(
            workflow_key="advisory_copilot_interaction",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and dependency_status.lotus_ai_ready,
            required_features=[
                "advisory.proposals.lifecycle",
                "advisory.advisory_copilot",
            ],
            dependency_keys=["lotus_ai"],
            degraded_reason=gated_dependency_unavailable_reason(
                enabled=lifecycle_enabled,
                ready=dependency_status.lotus_ai_ready,
                reason=LOTUS_AI_DEPENDENCY_UNAVAILABLE,
            ),
        ),
        WorkflowCapability(
            workflow_key="advisory_bank_demo_proof",
            enabled=lifecycle_enabled,
            operational_ready=dependency_status.bank_demo_operational_ready,
            required_features=[
                "advisory.proposals.lifecycle",
                "advisory.proposals.reviewed_narrative_evidence",
                "advisory.proposals.memo_evidence_pack",
                "advisory.policy_pack_catalog",
                "advisory.proposals.policy_evaluation",
                "advisory.advisor_cockpit",
                "advisory.advisory_copilot",
                "advisory.bank_demo_proof",
            ],
            dependency_keys=bank_demo_proof_dependency_keys(),
            degraded_reason=dependency_status.bank_demo_degraded_reason,
        ),
    ]


__all__ = ["build_evidence_product_workflow_capabilities"]
