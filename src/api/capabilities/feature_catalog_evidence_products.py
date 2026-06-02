from __future__ import annotations

from src.api.capabilities.degraded_reasons import (
    LOTUS_AI_DEPENDENCY_UNAVAILABLE,
    LOTUS_REPORT_DEPENDENCY_UNAVAILABLE,
    gated_dependency_unavailable_reason,
    lifecycle_disabled_reason,
)
from src.api.capabilities.dependencies import CapabilityDependencyStatus
from src.api.capabilities.models import FeatureCapability


def build_evidence_product_feature_capabilities(
    *,
    lifecycle_enabled: bool,
    dependency_status: CapabilityDependencyStatus,
) -> list[FeatureCapability]:
    return [
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
            degraded_reason=lifecycle_disabled_reason(lifecycle_enabled=lifecycle_enabled),
        ),
        FeatureCapability(
            key="advisory.proposals.memo_evidence_pack",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and dependency_status.lotus_report_ready,
            owner_service="ADVISORY",
            description=(
                "RFC-0024 advisor-use proposal memo evidence product with persisted memo evidence, "
                "projection, review posture, report-package handoff, archive refs, AI commentary "
                "lineage, and replay hashes. client-ready memo publication, external client "
                "communication, and full bank-demo/RFP package claims remain gated."
            ),
            fallback_mode="NONE",
            degraded_reason=gated_dependency_unavailable_reason(
                enabled=lifecycle_enabled,
                ready=dependency_status.lotus_report_ready,
                reason=LOTUS_REPORT_DEPENDENCY_UNAVAILABLE,
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
            degraded_reason=lifecycle_disabled_reason(lifecycle_enabled=lifecycle_enabled),
        ),
        FeatureCapability(
            key="advisory.proposals.policy_evaluation",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and dependency_status.lotus_report_ready,
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
            degraded_reason=gated_dependency_unavailable_reason(
                enabled=lifecycle_enabled,
                ready=dependency_status.lotus_report_ready,
                reason=LOTUS_REPORT_DEPENDENCY_UNAVAILABLE,
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
            degraded_reason=lifecycle_disabled_reason(lifecycle_enabled=lifecycle_enabled),
        ),
        FeatureCapability(
            key="advisory.advisory_copilot",
            enabled=lifecycle_enabled,
            operational_ready=lifecycle_enabled and dependency_status.lotus_ai_ready,
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
            degraded_reason=gated_dependency_unavailable_reason(
                enabled=lifecycle_enabled,
                ready=dependency_status.lotus_ai_ready,
                reason=LOTUS_AI_DEPENDENCY_UNAVAILABLE,
            ),
        ),
        FeatureCapability(
            key="advisory.bank_demo_proof",
            enabled=lifecycle_enabled,
            operational_ready=dependency_status.bank_demo_operational_ready,
            owner_service="ADVISORY",
            description=(
                "RFC-0028 bank-demo proof capability with source-owned scenario contract, "
                "supported-claim register, sanitized proof-pack capture, commercial/RFP/security "
                "material governance, and Gateway/Workbench canonical proof. Client-ready "
                "publication, external client communication, completed sign-off authority, "
                "and OMS order lifecycle remain blocked."
            ),
            fallback_mode="NONE",
            degraded_reason=dependency_status.bank_demo_degraded_reason,
        ),
    ]


__all__ = ["build_evidence_product_feature_capabilities"]
