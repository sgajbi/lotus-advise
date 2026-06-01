from datetime import UTC, date, datetime

from src.api.capabilities.degraded_reasons import (
    LOTUS_AI_DEPENDENCY_UNAVAILABLE,
    LOTUS_CORE_DEPENDENCY_UNAVAILABLE,
    LOTUS_REPORT_DEPENDENCY_UNAVAILABLE,
    LOTUS_RISK_DEPENDENCY_UNAVAILABLE,
    dependency_unavailable_reason,
    gated_dependency_unavailable_reason,
    lifecycle_disabled_reason,
)
from src.api.capabilities.dependencies import (
    DependencyMap,
    bank_demo_proof_dependency_keys,
    dependency_map,
    resolve_capability_dependency_status,
)
from src.api.capabilities.feature_catalog import build_feature_capabilities
from src.api.capabilities.models import (
    ConsumerSystem,
    IntegrationCapabilitiesResponse,
    OperationalReadiness,
    WorkflowCapability,
)
from src.api.capabilities.readiness import build_operational_readiness
from src.api.capabilities.runtime_flags import resolve_capability_runtime_flags
from src.api.capabilities.supportability import build_advisory_supportability


def build_workflow_capabilities(
    *,
    lifecycle_enabled: bool,
    ai_rationale_enabled: bool,
    dependencies: DependencyMap,
) -> list[WorkflowCapability]:
    dependency_status = resolve_capability_dependency_status(
        lifecycle_enabled=lifecycle_enabled,
        dependencies=dependencies,
    )

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
        WorkflowCapability(
            workflow_key="advisory_proposal_execution_handoff",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled,
            required_features=["advisory.proposals.execution_handoff"],
            dependency_keys=[],
            degraded_reason=None,
        ),
    ]


def build_integration_capabilities(
    *,
    consumer_system: ConsumerSystem,
    tenant_id: str,
    readiness: dict[str, object] | None = None,
) -> IntegrationCapabilitiesResponse:
    runtime_flags = resolve_capability_runtime_flags()
    readiness_payload = readiness if readiness is not None else build_operational_readiness()
    dependencies = dependency_map(readiness_payload)
    features = build_feature_capabilities(
        lifecycle_enabled=runtime_flags.lifecycle_enabled,
        async_enabled=runtime_flags.async_enabled,
        ai_rationale_enabled=runtime_flags.ai_rationale_enabled,
        dependencies=dependencies,
    )

    return IntegrationCapabilitiesResponse(
        contract_version="v1",
        source_service="lotus-advise",
        consumer_system=consumer_system,
        tenant_id=tenant_id,
        generated_at=datetime.now(UTC),
        as_of_date=date.today(),
        policy_version="advisory.v1",
        supported_input_modes=["stateless", "stateful"],
        features=features,
        workflows=build_workflow_capabilities(
            lifecycle_enabled=runtime_flags.lifecycle_enabled,
            ai_rationale_enabled=runtime_flags.ai_rationale_enabled,
            dependencies=dependencies,
        ),
        readiness=OperationalReadiness.model_validate(readiness_payload),
        supportability=build_advisory_supportability(
            readiness=readiness_payload,
            lifecycle_enabled=runtime_flags.lifecycle_enabled,
            features=features,
        ),
    )
