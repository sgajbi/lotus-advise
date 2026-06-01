import os
from datetime import UTC, date, datetime
from typing import cast

from src.api.capabilities.models import (
    AdvisorySupportability,
    ConsumerSystem,
    FeatureCapability,
    FreshnessBucket,
    IntegrationCapabilitiesResponse,
    OperationalReadiness,
    SupportabilityReason,
    SupportabilityState,
    WorkflowCapability,
)
from src.api.capabilities.readiness import build_operational_readiness
from src.api.observability import record_advisory_supportability
from src.integrations.lotus_core import lotus_core_fallback_mode

BANK_DEMO_PROOF_DEPENDENCY_KEYS = ("lotus_core", "lotus_risk", "lotus_ai", "lotus_report")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _dependency_rows(readiness: dict[str, object]) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], readiness.get("dependencies", []))


def _dependency_map(readiness: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(item["dependency_key"]): item
        for item in _dependency_rows(readiness)
        if "dependency_key" in item
    }


def _dependency_ready(dependencies: dict[str, dict[str, object]], dependency_key: str) -> bool:
    dependency = dependencies.get(dependency_key)
    if dependency is None:
        return False
    return bool(dependency.get("operational_ready"))


def _first_unready_dependency_reason(
    dependencies: dict[str, dict[str, object]],
    dependency_keys: tuple[str, ...],
    *,
    fallback_reason: str,
) -> str:
    for dependency_key in dependency_keys:
        if _dependency_ready(dependencies, dependency_key):
            continue
        dependency = dependencies.get(dependency_key)
        reason = dependency.get("degraded_reason") if dependency is not None else None
        if isinstance(reason, str) and reason:
            return reason
    return fallback_reason


def _bank_demo_proof_readiness(
    *,
    lifecycle_enabled: bool,
    dependencies: dict[str, dict[str, object]],
) -> tuple[bool, str | None]:
    operational_ready = lifecycle_enabled and all(
        _dependency_ready(dependencies, dependency_key)
        for dependency_key in BANK_DEMO_PROOF_DEPENDENCY_KEYS
    )
    if operational_ready:
        return True, None
    if not lifecycle_enabled:
        return False, "ADVISORY_LIFECYCLE_DISABLED"
    return False, _first_unready_dependency_reason(
        dependencies,
        BANK_DEMO_PROOF_DEPENDENCY_KEYS,
        fallback_reason="RFC0028_PROOF_DEPENDENCY_UNAVAILABLE",
    )


def build_advisory_supportability(
    *,
    readiness: dict[str, object],
    lifecycle_enabled: bool,
    features: list[FeatureCapability],
) -> AdvisorySupportability:
    dependency_rows = _dependency_rows(readiness)
    dependency_count = len(dependency_rows)
    ready_dependency_count = sum(
        1 for dependency in dependency_rows if bool(dependency.get("operational_ready"))
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


def build_feature_capabilities(
    *,
    lifecycle_enabled: bool,
    async_enabled: bool,
    ai_rationale_enabled: bool,
    dependencies: dict[str, dict[str, object]],
) -> list[FeatureCapability]:
    lotus_core_ready = _dependency_ready(dependencies, "lotus_core")
    lotus_risk_ready = _dependency_ready(dependencies, "lotus_risk")
    lotus_ai_ready = _dependency_ready(dependencies, "lotus_ai")
    lotus_report_ready = _dependency_ready(dependencies, "lotus_report")
    bank_demo_operational_ready, bank_demo_degraded_reason = _bank_demo_proof_readiness(
        lifecycle_enabled=lifecycle_enabled,
        dependencies=dependencies,
    )

    return [
        FeatureCapability(
            key="advisory.proposals.simulation",
            enabled=True,
            operational_ready=lotus_core_ready,
            owner_service="LOTUS_CORE",
            description=(
                "Canonical advisory proposal simulation through lotus-core; "
                "lotus-advise remains the workflow and API owner."
            ),
            fallback_mode=lotus_core_fallback_mode(),
            degraded_reason=(None if lotus_core_ready else "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"),
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
            operational_ready=lotus_core_ready,
            owner_service="ADVISORY",
            description=(
                "Stateful advisory workspace evaluation through Lotus Core context resolution."
            ),
            fallback_mode=lotus_core_fallback_mode(),
            degraded_reason=(None if lotus_core_ready else "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"),
        ),
        FeatureCapability(
            key="advisory.workspaces.ai_rationale",
            enabled=ai_rationale_enabled,
            operational_ready=ai_rationale_enabled and lotus_ai_ready,
            owner_service="ADVISORY",
            description="Evidence-grounded advisory workspace rationale through Lotus AI.",
            fallback_mode="NONE",
            degraded_reason=(
                None
                if not ai_rationale_enabled or lotus_ai_ready
                else "LOTUS_AI_DEPENDENCY_UNAVAILABLE"
            ),
        ),
        FeatureCapability(
            key="advisory.proposals.risk_lens",
            enabled=True,
            operational_ready=lotus_risk_ready,
            owner_service="LOTUS_RISK",
            description="Proposal before/after concentration risk lens through lotus-risk.",
            fallback_mode="LOCAL_RISK_FALLBACK",
            degraded_reason=(None if lotus_risk_ready else "LOTUS_RISK_DEPENDENCY_UNAVAILABLE"),
        ),
        FeatureCapability(
            key="advisory.proposals.reporting",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and lotus_report_ready,
            owner_service="LOTUS_REPORT",
            description=(
                "Advisory proposal report-request integration boundary through lotus-report."
            ),
            fallback_mode="NONE",
            degraded_reason=(
                None
                if not lifecycle_enabled or lotus_report_ready
                else "LOTUS_REPORT_DEPENDENCY_UNAVAILABLE"
            ),
        ),
        FeatureCapability(
            key="advisory.proposals.reviewed_narrative_evidence",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled,
            owner_service="ADVISORY",
            description=(
                "RFC-0023 advisor-review proposal narrative evidence product with persisted "
                "narrative, source hashes, review posture, replay evidence, and reviewed "
                "report-request package support. Compliance-review, client-draft, client-ready "
                "publication, and canonical demo proof remain gated."
            ),
            fallback_mode="NONE",
            degraded_reason=None if lifecycle_enabled else "ADVISORY_LIFECYCLE_DISABLED",
        ),
        FeatureCapability(
            key="advisory.proposals.memo_evidence_pack",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and lotus_report_ready,
            owner_service="ADVISORY",
            description=(
                "RFC-0024 advisor-use proposal memo evidence product with persisted memo evidence, "
                "projection, review posture, report-package handoff, archive refs, AI commentary "
                "lineage, and replay hashes. client-ready memo publication, external client "
                "communication, and full bank-demo/RFP package claims remain gated."
            ),
            fallback_mode="NONE",
            degraded_reason=(
                None
                if not lifecycle_enabled or lotus_report_ready
                else "LOTUS_REPORT_DEPENDENCY_UNAVAILABLE"
            ),
        ),
        FeatureCapability(
            key="advisory.policy_pack_catalog",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled,
            owner_service="ADVISORY",
            description=(
                "RFC-0025 policy-pack catalog with reference-pack metadata, schema validation, "
                "hash-backed activation posture, maker-checker controls where configured, and "
                "catalog audit events."
            ),
            fallback_mode="NONE",
            degraded_reason=None if lifecycle_enabled else "ADVISORY_LIFECYCLE_DISABLED",
        ),
        FeatureCapability(
            key="advisory.proposals.policy_evaluation",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and lotus_report_ready,
            owner_service="ADVISORY",
            description=(
                "RFC-0025 advisor/compliance policy evaluation data product with finalized "
                "records, replay, review queue, sign-off source packages, workflow posture, "
                "signed-off report-package lineage, bounded AI evidence, Gateway routing, and "
                "Workbench visibility. Completed approval/waiver authority, completed sign-off "
                "authority, client-ready publication, and external client communication remain "
                "gated."
            ),
            fallback_mode="NONE",
            degraded_reason=(
                None
                if not lifecycle_enabled or lotus_report_ready
                else "LOTUS_REPORT_DEPENDENCY_UNAVAILABLE"
            ),
        ),
        FeatureCapability(
            key="advisory.advisor_cockpit",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled,
            owner_service="ADVISORY",
            description=(
                "RFC-0026 advisor cockpit operating workflow with source-owned action items, "
                "operating snapshot, supportability posture, meeting-preparation evidence, "
                "Gateway/Workbench canonical proof, and bounded acknowledgement. Client-ready "
                "publication, external client communication, CRM system-of-record behavior, "
                "OMS order lifecycle, completed policy approval authority, and full RFC-0028 "
                "demo/RFP package claims remain gated."
            ),
            fallback_mode="NONE",
            degraded_reason=None if lifecycle_enabled else "ADVISORY_LIFECYCLE_DISABLED",
        ),
        FeatureCapability(
            key="advisory.advisory_copilot",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and lotus_ai_ready,
            owner_service="ADVISORY",
            description=(
                "RFC-0027 governed advisory copilot interaction product with source-backed "
                "proposal-version evidence packets, governed lotus-ai workflow-pack execution, "
                "persisted run/review posture, guardrails, Gateway/Workbench canonical proof, "
                "and active AdvisoryCopilotInteractionRecord:v1 trust telemetry. Client-ready "
                "publication, external client communication, policy approval/sign-off authority, "
                "OMS order lifecycle, fills, settlement, and full RFC-0028 demo/RFP package "
                "claims remain gated."
            ),
            fallback_mode="NONE",
            degraded_reason=(
                None
                if not lifecycle_enabled or lotus_ai_ready
                else "LOTUS_AI_DEPENDENCY_UNAVAILABLE"
            ),
        ),
        FeatureCapability(
            key="advisory.bank_demo_proof",
            enabled=lifecycle_enabled,
            operational_ready=bank_demo_operational_ready,
            owner_service="ADVISORY",
            description=(
                "RFC-0028 bank-demo proof capability with source-owned scenario contract, "
                "supported-claim register, sanitized proof-pack capture, commercial/RFP/security "
                "material governance, and Gateway/Workbench canonical proof. Client-ready "
                "publication, external client communication, completed sign-off authority, "
                "and OMS order lifecycle remain blocked."
            ),
            fallback_mode="NONE",
            degraded_reason=bank_demo_degraded_reason,
        ),
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
            degraded_reason=None if lifecycle_enabled else "ADVISORY_LIFECYCLE_DISABLED",
        ),
    ]


def build_workflow_capabilities(
    *,
    lifecycle_enabled: bool,
    ai_rationale_enabled: bool,
    dependencies: dict[str, dict[str, object]],
) -> list[WorkflowCapability]:
    lotus_core_ready = _dependency_ready(dependencies, "lotus_core")
    lotus_risk_ready = _dependency_ready(dependencies, "lotus_risk")
    lotus_ai_ready = _dependency_ready(dependencies, "lotus_ai")
    lotus_report_ready = _dependency_ready(dependencies, "lotus_report")
    bank_demo_operational_ready, bank_demo_degraded_reason = _bank_demo_proof_readiness(
        lifecycle_enabled=lifecycle_enabled,
        dependencies=dependencies,
    )

    return [
        WorkflowCapability(
            workflow_key="advisory_proposal_simulation",
            enabled=True,
            operational_ready=lotus_core_ready,
            required_features=["advisory.proposals.simulation"],
            dependency_keys=["lotus_core"],
            degraded_reason=(None if lotus_core_ready else "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"),
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
            operational_ready=lotus_core_ready,
            required_features=["advisory.workspaces.stateful"],
            dependency_keys=["lotus_core"],
            degraded_reason=(None if lotus_core_ready else "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"),
        ),
        WorkflowCapability(
            workflow_key="advisory_workspace_ai_rationale",
            enabled=ai_rationale_enabled,
            operational_ready=ai_rationale_enabled and lotus_ai_ready,
            required_features=["advisory.workspaces.ai_rationale"],
            dependency_keys=["lotus_ai"],
            degraded_reason=(
                None
                if not ai_rationale_enabled or lotus_ai_ready
                else "LOTUS_AI_DEPENDENCY_UNAVAILABLE"
            ),
        ),
        WorkflowCapability(
            workflow_key="advisory_proposal_risk_lens",
            enabled=True,
            operational_ready=lotus_risk_ready,
            required_features=["advisory.proposals.risk_lens"],
            dependency_keys=["lotus_risk"],
            degraded_reason=(None if lotus_risk_ready else "LOTUS_RISK_DEPENDENCY_UNAVAILABLE"),
        ),
        WorkflowCapability(
            workflow_key="advisory_proposal_reporting",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and lotus_report_ready,
            required_features=["advisory.proposals.reporting"],
            dependency_keys=["lotus_report"],
            degraded_reason=(
                None
                if not lifecycle_enabled or lotus_report_ready
                else "LOTUS_REPORT_DEPENDENCY_UNAVAILABLE"
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
            degraded_reason=None if lifecycle_enabled else "ADVISORY_LIFECYCLE_DISABLED",
        ),
        WorkflowCapability(
            workflow_key="advisory_proposal_memo_evidence_pack",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and lotus_report_ready,
            required_features=[
                "advisory.proposals.lifecycle",
                "advisory.proposals.memo_evidence_pack",
                "advisory.proposals.reporting",
            ],
            dependency_keys=["lotus_report"],
            degraded_reason=(
                None
                if not lifecycle_enabled or lotus_report_ready
                else "LOTUS_REPORT_DEPENDENCY_UNAVAILABLE"
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
            degraded_reason=None if lifecycle_enabled else "ADVISORY_LIFECYCLE_DISABLED",
        ),
        WorkflowCapability(
            workflow_key="advisory_policy_evaluation",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and lotus_report_ready,
            required_features=[
                "advisory.proposals.lifecycle",
                "advisory.policy_pack_catalog",
                "advisory.proposals.policy_evaluation",
                "advisory.proposals.reporting",
            ],
            dependency_keys=["lotus_report"],
            degraded_reason=(
                None
                if not lifecycle_enabled or lotus_report_ready
                else "LOTUS_REPORT_DEPENDENCY_UNAVAILABLE"
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
            degraded_reason=None if lifecycle_enabled else "ADVISORY_LIFECYCLE_DISABLED",
        ),
        WorkflowCapability(
            workflow_key="advisory_copilot_interaction",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and lotus_ai_ready,
            required_features=[
                "advisory.proposals.lifecycle",
                "advisory.advisory_copilot",
            ],
            dependency_keys=["lotus_ai"],
            degraded_reason=(
                None
                if not lifecycle_enabled or lotus_ai_ready
                else "LOTUS_AI_DEPENDENCY_UNAVAILABLE"
            ),
        ),
        WorkflowCapability(
            workflow_key="advisory_bank_demo_proof",
            enabled=lifecycle_enabled,
            operational_ready=bank_demo_operational_ready,
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
            dependency_keys=list(BANK_DEMO_PROOF_DEPENDENCY_KEYS),
            degraded_reason=bank_demo_degraded_reason,
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
    lifecycle_enabled = _env_bool("PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED", True)
    async_enabled = _env_bool("PROPOSAL_ASYNC_OPERATIONS_ENABLED", True)
    ai_rationale_enabled = _env_bool("LOTUS_AI_WORKSPACE_RATIONALE_ENABLED", True)
    readiness_payload = readiness if readiness is not None else build_operational_readiness()
    dependencies = _dependency_map(readiness_payload)
    features = build_feature_capabilities(
        lifecycle_enabled=lifecycle_enabled,
        async_enabled=async_enabled,
        ai_rationale_enabled=ai_rationale_enabled,
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
            lifecycle_enabled=lifecycle_enabled,
            ai_rationale_enabled=ai_rationale_enabled,
            dependencies=dependencies,
        ),
        readiness=OperationalReadiness.model_validate(readiness_payload),
        supportability=build_advisory_supportability(
            readiness=readiness_payload,
            lifecycle_enabled=lifecycle_enabled,
            features=features,
        ),
    )
