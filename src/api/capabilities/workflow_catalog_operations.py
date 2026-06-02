from __future__ import annotations

from src.api.capabilities.models import WorkflowCapability


def build_operational_workflow_capabilities(
    *,
    lifecycle_enabled: bool,
) -> list[WorkflowCapability]:
    return [
        WorkflowCapability(
            workflow_key="advisory_proposal_execution_handoff",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled,
            required_features=["advisory.proposals.execution_handoff"],
            dependency_keys=[],
            degraded_reason=None,
        ),
    ]


__all__ = ["build_operational_workflow_capabilities"]
