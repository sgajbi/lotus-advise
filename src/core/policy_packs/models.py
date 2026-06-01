from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.policy_packs.catalog_models import (
    PolicyPackActivationRequest as PolicyPackActivationRequest,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackActivationResponse as PolicyPackActivationResponse,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackActivationState as PolicyPackActivationState,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackAuditEvent as PolicyPackAuditEvent,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackDetailResponse as PolicyPackDetailResponse,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackEventType as PolicyPackEventType,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackListResponse as PolicyPackListResponse,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackSummary as PolicyPackSummary,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackValidationRequest as PolicyPackValidationRequest,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackValidationResponse as PolicyPackValidationResponse,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackValidationStatus as PolicyPackValidationStatus,
)
from src.core.policy_packs.evaluation_models import (
    PolicyApplicabilityStatus as PolicyApplicabilityStatus,
)
from src.core.policy_packs.evaluation_models import (
    PolicyEvaluationStatus as PolicyEvaluationStatus,
)
from src.core.policy_packs.evaluation_models import (
    PolicyPackApplicabilityResult as PolicyPackApplicabilityResult,
)
from src.core.policy_packs.evaluation_models import (
    PolicyPackEvaluationResponse as PolicyPackEvaluationResponse,
)
from src.core.policy_packs.evaluation_models import (
    PolicyRuleEvaluationResult as PolicyRuleEvaluationResult,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationAuditEvent as PolicyEvaluationAuditEvent,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationCreateRequest as PolicyEvaluationCreateRequest,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationEventRequest as PolicyEvaluationEventRequest,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationEventType as PolicyEvaluationEventType,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationPersistenceResult as PolicyEvaluationPersistenceResult,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationRecord as PolicyEvaluationRecord,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationReplayRequest as PolicyEvaluationReplayRequest,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationReplayResponse as PolicyEvaluationReplayResponse,
)
from src.core.policy_packs.workflow_models import (
    PolicyEvaluationRequirementProjection as PolicyEvaluationRequirementProjection,
)
from src.core.policy_packs.workflow_models import (
    PolicyEvaluationRequirementStatus as PolicyEvaluationRequirementStatus,
)
from src.core.policy_packs.workflow_models import (
    PolicyEvaluationSignOffDecision as PolicyEvaluationSignOffDecision,
)
from src.core.policy_packs.workflow_models import (
    PolicyEvaluationSignOffDecisionRequest as PolicyEvaluationSignOffDecisionRequest,
)
from src.core.policy_packs.workflow_models import (
    PolicyEvaluationSignOffDecisionResponse as PolicyEvaluationSignOffDecisionResponse,
)
from src.core.policy_packs.workflow_models import (
    PolicyEvaluationSignOffStatus as PolicyEvaluationSignOffStatus,
)
from src.core.policy_packs.workflow_models import (
    PolicyEvaluationWorkflowResponse as PolicyEvaluationWorkflowResponse,
)
from src.core.proposals.response_models import ProposalReportResponse


class PolicyEvaluationLineageResponse(BaseModel):
    evaluation_id: str = Field(
        description="Policy evaluation record identifier.",
        examples=["pev_123abc"],
    )
    proposal_id: str = Field(description="Proposal identifier.", examples=["pp_001"])
    proposal_version_id: str = Field(
        description="Immutable proposal version identifier.",
        examples=["ppv_001"],
    )
    policy_pack_id: str = Field(
        description="Policy pack identifier.",
        examples=["SG_PRIVATE_BANKING_REFERENCE"],
    )
    policy_version: str = Field(description="Pinned policy-pack version.", examples=["2026.05"])
    policy_content_hash: str = Field(
        description="Pinned policy-pack content hash.",
        examples=["sha256:policy-pack-content"],
    )
    source_evidence_hash: str = Field(
        description="Source evidence hash evaluated.",
        examples=["sha256:source-evidence"],
    )
    evaluation_hash: str = Field(
        description="Immutable policy evaluation hash.",
        examples=["sha256:policy-evaluation"],
    )
    rule_result_hashes: dict[str, str] = Field(
        description="Per-rule result hashes retained for material field certification.",
        examples=[{"SG_COMPLEX_PRODUCT_DISCLOSURE_REVIEW": "sha256:rule-result"}],
    )
    source_refs: list[str] = Field(
        description="Source authority and evidence refs used.",
        examples=[["lotus-core:core_product_eligibility_target_market_complexity"]],
    )
    source_gaps: list[str] = Field(
        description="Missing source evidence retained in the record.",
        examples=[["client_consent:SG_STRUCTURED_NOTE"]],
    )
    audit_events: list[PolicyEvaluationAuditEvent] = Field(
        description="Append-only finalization, review, sign-off, and report/archive events.",
        examples=[[{"event_type": "POLICY_EVALUATION_FINALIZED"}]],
    )
    lineage_posture: dict[str, Any] = Field(
        description="Support boundary and publication posture for this policy lineage.",
        examples=[{"client_ready_publication": "BLOCKED"}],
    )


class PolicyEvaluationReviewQueueResponse(BaseModel):
    items: list[PolicyEvaluationRecord] = Field(
        description=(
            "Policy evaluation records requiring advisor, compliance, or supervisory review."
        ),
        examples=[[{"evaluation_id": "pev_123abc", "evaluation_status": "PENDING_REVIEW"}]],
    )
    queue_posture: dict[str, Any] = Field(
        description="Review queue support boundary and unsupported downstream surfaces.",
        examples=[
            {
                "gateway_supported": True,
                "gateway_support": "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_BFF",
                "workbench_supported": True,
                "workbench_support": "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_ONLY_UI",
                "client_ready_publication": "BLOCKED",
            }
        ],
    )


class PolicyEvaluationSignOffPackageResponse(BaseModel):
    evaluation: PolicyEvaluationRecord = Field(
        description="Finalized policy evaluation record used as the sign-off source.",
        examples=[{"evaluation_id": "pev_123abc"}],
    )
    lineage: PolicyEvaluationLineageResponse = Field(
        description="Hash-backed lineage and append-only event trail for sign-off review.",
        examples=[{"evaluation_id": "pev_123abc"}],
    )
    package_posture: dict[str, Any] = Field(
        description=(
            "Current sign-off package realization boundary. Advise exposes the certified source "
            "package and signed-off report-package handoff, but client-ready publication remains "
            "blocked."
        ),
        examples=[
            {
                "report_render_archive_realization": (
                    "SUPPORTED_BY_RFC0025_SLICE10_SIGNED_OFF_PACKAGE_HANDOFF"
                ),
                "client_ready_publication": "BLOCKED",
            }
        ],
    )


class PolicyEvaluationReportPackageRequest(BaseModel):
    requested_by: str = Field(
        description="Actor requesting policy sign-off report/render/archive materialization.",
        examples=["policy_checker_1"],
    )
    portfolio_id: str = Field(
        description="Portfolio identifier for the policy report package.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    source_evaluation_hash: str = Field(
        description="Immutable policy evaluation hash inspected by the requester.",
        examples=["sha256:policy-evaluation"],
    )
    requested_output_formats: list[str] = Field(
        default_factory=lambda: ["pdf"],
        min_length=1,
        description="Output formats requested from lotus-report for the policy package.",
        examples=[["pdf"]],
    )
    client_ready_document_requested: bool = Field(
        default=False,
        description=(
            "Whether the caller is requesting client-ready document release. This remains blocked "
            "by the RFC-0025 and RFC-0028 client-ready publication controls."
        ),
        examples=[False],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured report-package request reason retained in policy lineage.",
        examples=[{"purpose": "compliance sign-off package"}],
    )


class PolicyEvaluationReportPackageResponse(BaseModel):
    evaluation: PolicyEvaluationRecord = Field(
        description="Policy evaluation record after report-package event recording."
    )
    report_package_event: PolicyEvaluationAuditEvent = Field(
        description="Created or replayed report/render/archive reference event."
    )
    report: ProposalReportResponse = Field(
        description="lotus-report job handle and materialization references."
    )
    replayed: bool = Field(
        description="Whether this request replayed an existing idempotent report-package event.",
        examples=[False],
    )


class PolicyEvaluationAiEvidenceRequest(BaseModel):
    requested_by: str = Field(
        description="Actor requesting bounded AI policy-evidence commentary.",
        examples=["policy_checker_1"],
    )
    source_evaluation_hash: str = Field(
        description="Immutable policy evaluation hash inspected by the requester.",
        examples=["sha256:policy-evaluation"],
    )
    requested_actions: list[str] = Field(
        default_factory=lambda: ["SUMMARIZE_POLICY_POSTURE"],
        min_length=1,
        description=(
            "Bounded AI evidence actions requested from lotus-ai. Mutation, approval, waiver, "
            "client-ready, and unsupported regulatory-claim actions are rejected."
        ),
        examples=[["SUMMARIZE_POLICY_POSTURE", "EXPLAIN_OPEN_REQUIREMENTS"]],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured AI evidence request reason retained in policy lineage.",
        examples=[{"purpose": "policy evidence explanation"}],
    )


class PolicyEvaluationAiEvidenceResponse(BaseModel):
    evaluation: PolicyEvaluationRecord = Field(
        description="Policy evaluation record after AI evidence lineage recording."
    )
    ai_event: PolicyEvaluationAuditEvent = Field(
        description="Created or replayed policy AI evidence event."
    )
    policy_evidence: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Bounded AI policy-evidence payload or deterministic unavailable posture. This "
            "payload is non-authoritative and cannot change policy status, rule results, "
            "approvals, waivers, disclosures, or consent posture."
        ),
    )
    replayed: bool = Field(
        description="Whether this request replayed an existing idempotent AI evidence event.",
        examples=[False],
    )
