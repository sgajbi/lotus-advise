from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.policy_packs.ai_models import (
    PolicyEvaluationAiEvidenceRequest as PolicyEvaluationAiEvidenceRequest,
)
from src.core.policy_packs.ai_models import (
    PolicyEvaluationAiEvidenceResponse as PolicyEvaluationAiEvidenceResponse,
)
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
from src.core.policy_packs.reporting_models import (
    PolicyEvaluationReportPackageRequest as PolicyEvaluationReportPackageRequest,
)
from src.core.policy_packs.reporting_models import (
    PolicyEvaluationReportPackageResponse as PolicyEvaluationReportPackageResponse,
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
