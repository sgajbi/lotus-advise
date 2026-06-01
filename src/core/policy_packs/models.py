from __future__ import annotations

from typing import Any, Literal

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
from src.core.proposals.response_models import ProposalReportResponse

PolicyEvaluationStatus = Literal["READY", "PENDING_REVIEW", "BLOCKED", "NOT_APPLICABLE"]
PolicyEvaluationRequirementStatus = Literal["OPEN", "SATISFIED", "BLOCKED"]
PolicyEvaluationSignOffStatus = Literal[
    "READY_FOR_SIGN_OFF",
    "SIGNED_OFF",
    "PENDING_REVIEW",
    "BLOCKED",
]
PolicyEvaluationSignOffDecision = Literal[
    "APPROVE_FOR_POLICY_SIGN_OFF",
    "REQUEST_MORE_EVIDENCE",
    "REJECT_POLICY_SIGN_OFF",
]
PolicyApplicabilityStatus = Literal["APPLICABLE", "NOT_APPLICABLE", "BLOCKED"]
PolicyEvaluationEventType = Literal[
    "POLICY_EVALUATION_FINALIZED",
    "POLICY_EVALUATION_REVIEW_RECORDED",
    "POLICY_EVALUATION_SIGN_OFF_RECORDED",
    "POLICY_EVALUATION_REPORT_ARCHIVE_RECORDED",
    "POLICY_EVALUATION_AI_EVIDENCE_RECORDED",
]


class PolicyPackApplicabilityResult(BaseModel):
    status: PolicyApplicabilityStatus = Field(
        description="Whether this policy pack applies to the proposal evidence.",
        examples=["APPLICABLE"],
    )
    matched_selectors: dict[str, str] = Field(
        default_factory=dict,
        description="Applicability selectors matched from source-owned proposal evidence.",
        examples=[{"jurisdiction": "SG", "client_segment": "ACCREDITED_INVESTOR"}],
    )
    missing_evidence: list[str] = Field(
        default_factory=list,
        description="Source-owned selector evidence missing before applicability can be decided.",
        examples=[["jurisdiction"]],
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Domain reason codes explaining applicability posture.",
        examples=[["POLICY_PACK_APPLIES_TO_PROPOSAL_CONTEXT"]],
    )


class PolicyRuleEvaluationResult(BaseModel):
    rule_id: str = Field(description="Policy-pack rule identifier.")
    status: PolicyEvaluationStatus = Field(
        description="Rule evaluation posture for this proposal evidence.",
        examples=["PENDING_REVIEW"],
    )
    severity: str = Field(description="Policy-pack rule severity.", examples=["BLOCKING"])
    outcome: str = Field(
        description="Domain outcome for the evaluated rule; never a generic pass/fail claim.",
        examples=["DISCLOSURE_AND_CONSENT_REVIEW_REQUIRED"],
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Concrete proposal evidence references used by this result.",
    )
    source_authority_refs: list[str] = Field(
        default_factory=list,
        description="Source-owner references backing the rule result.",
        examples=[["lotus-core:core_product_eligibility_target_market_complexity"]],
    )
    missing_evidence: list[str] = Field(
        default_factory=list,
        description="Missing evidence that prevents a positive policy outcome.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes explaining rule status.",
    )
    required_actions: list[str] = Field(
        default_factory=list,
        description="Advisor, policy, compliance, or supervisory actions required by the rule.",
    )


class PolicyPackEvaluationResponse(BaseModel):
    contract_version: str = Field(
        description="Internal RFC-0025 policy evaluation engine contract version.",
        examples=["rfc0025.policy-evaluation-engine.v1"],
    )
    policy_pack: PolicyPackSummary = Field(description="Evaluated active policy pack.")
    evaluation_status: PolicyEvaluationStatus = Field(
        description="Aggregate evaluation posture across applicable rules.",
        examples=["PENDING_REVIEW"],
    )
    applicability: PolicyPackApplicabilityResult = Field(
        description="Source-backed applicability result for the policy pack."
    )
    source_posture: dict[str, Any] = Field(
        description="Policy source-readiness posture consumed by the evaluator.",
        examples=[{"contract_version": "rfc0025.policy-source-readiness.v1"}],
    )
    rule_results: list[PolicyRuleEvaluationResult] = Field(
        description="Material rule results with source refs, gaps, reasons, and required actions."
    )
    supportability: dict[str, Any] = Field(
        description="Current support boundary for the internal policy evaluation engine.",
        examples=[{"policy_evaluation_api": "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API"}],
    )


class PolicyEvaluationAuditEvent(BaseModel):
    event_id: str = Field(
        description="Append-only policy evaluation event identifier.",
        examples=["peev_000001"],
    )
    evaluation_id: str = Field(
        description="Policy evaluation record identifier.",
        examples=["pev_123abc"],
    )
    proposal_id: str = Field(
        description="Proposal identifier evaluated by the policy record.",
        examples=["pp_001"],
    )
    proposal_version_id: str = Field(
        description="Immutable proposal version identifier evaluated by the policy record.",
        examples=["ppv_001"],
    )
    event_type: PolicyEvaluationEventType = Field(
        description="Policy evaluation event type.",
        examples=["POLICY_EVALUATION_FINALIZED"],
    )
    actor_id: str = Field(
        description="Actor that created the event.",
        examples=["advisor_1"],
    )
    occurred_at: str = Field(
        description="UTC ISO8601 timestamp for the event.",
        examples=["2026-05-26T01:00:00+00:00"],
    )
    content_hash: str = Field(
        description="Canonical hash of the immutable finalized policy evaluation record.",
        examples=["sha256:policy-evaluation-record"],
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Idempotency key supplied for replay-safe event handling.",
        examples=["policy-evaluation-finalize-001"],
    )
    reason_json: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured policy event reason, source refs, and downstream refs.",
    )


class PolicyEvaluationRecord(BaseModel):
    evaluation_id: str = Field(
        description="Deterministic policy evaluation record identifier.",
        examples=["pev_123abc"],
    )
    proposal_id: str = Field(description="Proposal identifier.", examples=["pp_001"])
    proposal_version_id: str = Field(
        description="Immutable proposal version identifier.",
        examples=["ppv_001"],
    )
    portfolio_id: str = Field(
        description="Portfolio identifier from the evaluated source evidence.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    policy_pack_id: str = Field(
        description="Policy pack identifier used for the evaluation.",
        examples=["SG_PRIVATE_BANKING_REFERENCE"],
    )
    policy_version: str = Field(
        description="Policy pack version used for the evaluation.",
        examples=["2026.05"],
    )
    generated_at: str = Field(
        description="UTC ISO8601 timestamp when the evaluation record was finalized.",
        examples=["2026-05-26T01:00:00+00:00"],
    )
    created_by: str = Field(
        description="Actor that finalized the policy evaluation record.",
        examples=["advisor_1"],
    )
    evaluation_status: PolicyEvaluationStatus = Field(
        description="Aggregate evaluation posture persisted for replay and audit.",
        examples=["PENDING_REVIEW"],
    )
    policy_content_hash: str = Field(
        description="Canonical content hash of the policy-pack version at evaluation time.",
        examples=["sha256:policy-pack-content"],
    )
    source_evidence_hash: str = Field(
        description="Canonical hash of the source evidence evaluated by the policy pack.",
        examples=["sha256:source-evidence"],
    )
    evaluation_hash: str = Field(
        description="Canonical hash of immutable policy evaluation truth.",
        examples=["sha256:policy-evaluation"],
    )
    rule_result_hashes: dict[str, str] = Field(
        default_factory=dict,
        description="Canonical hash of each persisted rule result by rule identifier.",
    )
    evaluation_json: dict[str, Any] = Field(
        description="Persisted `PolicyPackEvaluationResponse` JSON.",
    )
    source_refs: list[str] = Field(
        default_factory=list,
        description="Source authority and evidence references used by the evaluation.",
    )
    source_gaps: list[str] = Field(
        default_factory=list,
        description="Missing source evidence retained in the finalized record.",
    )
    approval_dependencies: list[str] = Field(
        default_factory=list,
        description="Policy-driven approval or review actions required by the evaluation.",
    )
    disclosure_requirements: list[str] = Field(
        default_factory=list,
        description="Disclosure requirements identified by policy evaluation.",
    )
    consent_requirements: list[str] = Field(
        default_factory=list,
        description="Client consent requirements identified by policy evaluation.",
    )
    review_events_json: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Append-only review events attached to this evaluation.",
    )
    sign_off_events_json: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Append-only sign-off events attached to this evaluation.",
    )
    report_archive_refs_json: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Append-only report, render, and archive refs attached to this evaluation.",
    )
    replay_metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        description="Replay metadata proving policy version, hashes, and source refs.",
    )


class PolicyEvaluationPersistenceResult(BaseModel):
    record: PolicyEvaluationRecord = Field(description="Persisted policy evaluation record.")
    created: bool = Field(description="Whether this call created the finalized record.")
    replayed: bool = Field(
        description="Whether this call replayed a prior idempotent finalize request."
    )
    audit_event: PolicyEvaluationAuditEvent | None = Field(
        default=None,
        description="Audit event created or replayed for this persistence command.",
    )


class PolicyEvaluationReplayResponse(BaseModel):
    evaluation_id: str = Field(description="Policy evaluation record identifier.")
    replay_contract_version: str = Field(
        description="Internal replay contract version.",
        examples=["rfc0025.policy-evaluation-persistence.v1"],
    )
    policy_pack_id: str = Field(description="Policy pack identifier.")
    policy_version: str = Field(description="Policy version pinned by the record.")
    source_refs: list[str] = Field(description="Persisted source refs used for replay proof.")
    source_gaps: list[str] = Field(description="Persisted source gaps used for replay proof.")
    hash_comparison: dict[str, Any] = Field(
        description="Stored versus replayed hash comparison for policy, source, and result truth.",
    )
    replay_metadata: dict[str, Any] = Field(description="Persisted replay metadata.")


class PolicyEvaluationCreateRequest(BaseModel):
    policy_pack_id: str = Field(
        description="Policy pack identifier to evaluate against the supplied proposal evidence.",
        examples=["GLOBAL_PRIVATE_BANKING_BASELINE"],
    )
    policy_version: str = Field(
        description="Immutable policy-pack version to evaluate.",
        examples=["2026.05"],
    )
    created_by: str = Field(
        description="Advisor or operator creating the finalized policy evaluation record.",
        examples=["advisor_1"],
    )
    evidence_bundle: dict[str, Any] = Field(
        description=(
            "Source-backed proposal evidence bundle containing advisory context, proposed trades, "
            "source-readiness posture, risk evidence, disclosures, and conflict evidence."
        ),
        examples=[
            {
                "context_resolution": {
                    "advisory_policy_context": {
                        "jurisdiction": "SG",
                        "client_classification": "ACCREDITED_INVESTOR",
                    }
                },
                "inputs": {"proposed_trades": [{"instrument_id": "US_EQ_ETF", "side": "BUY"}]},
            }
        ],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured business reason retained in the finalized audit event.",
        examples=[{"purpose": "advisor suitability review"}],
    )


class PolicyEvaluationEventRequest(BaseModel):
    event_type: PolicyEvaluationEventType = Field(
        description="Append-only policy evaluation event type to record.",
        examples=["POLICY_EVALUATION_REVIEW_RECORDED"],
    )
    actor_id: str = Field(
        description="Actor recording the review, sign-off, or report/archive event.",
        examples=["compliance_1"],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured event reason, decision posture, and downstream reference details.",
        examples=[{"review_action": "REQUEST_MORE_EVIDENCE"}],
    )


class PolicyEvaluationReplayRequest(BaseModel):
    evidence_bundle: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional current evidence bundle for hash comparison against the finalized record. "
            "Omit to compare only pinned policy-version and stored source/evaluation hashes."
        ),
        examples=[{"inputs": {"proposed_trades": [{"instrument_id": "US_EQ_ETF"}]}}],
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


class PolicyEvaluationRequirementProjection(BaseModel):
    requirement_id: str = Field(
        description="Policy approval, disclosure, consent, or conflict requirement identifier.",
        examples=["REVIEW_DISCLOSURE:SG_STRUCTURED_NOTE"],
    )
    requirement_type: str = Field(
        description="Requirement family such as approval, disclosure, consent, or conflict.",
        examples=["disclosure"],
    )
    status: PolicyEvaluationRequirementStatus = Field(
        description="Current requirement posture derived from policy evidence and review events.",
        examples=["OPEN"],
    )
    owner_role: str = Field(
        description="Expected owner role for reviewing or satisfying this requirement.",
        examples=["INVESTMENT_COUNSELLOR"],
    )
    review_sla: str | None = Field(
        default=None,
        description="Configured review service level where known.",
        examples=["P1D"],
    )
    due_at: str | None = Field(
        default=None,
        description="UTC ISO8601 due time derived from the evaluation timestamp and review SLA.",
        examples=["2026-05-27T01:00:00+00:00"],
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Reason codes explaining the requirement posture.",
        examples=[["POLICY_REQUIREMENT_OPEN"]],
    )


class PolicyEvaluationWorkflowResponse(BaseModel):
    evaluation_id: str = Field(
        description="Policy evaluation record identifier.",
        examples=["pev_123abc"],
    )
    proposal_id: str = Field(description="Proposal identifier.", examples=["pp_001"])
    proposal_version_id: str = Field(
        description="Immutable proposal version identifier.",
        examples=["ppv_001"],
    )
    evaluation_status: PolicyEvaluationStatus = Field(
        description="Aggregate policy evaluation status.",
        examples=["PENDING_REVIEW"],
    )
    approval_dependencies: list[PolicyEvaluationRequirementProjection] = Field(
        description="Approval and review dependencies derived from policy outcomes.",
        examples=[[{"requirement_id": "REVIEW_DISCLOSURE:SG_STRUCTURED_NOTE"}]],
    )
    disclosure_requirements: list[PolicyEvaluationRequirementProjection] = Field(
        description="Disclosure requirements that must stay visible through memo/report prep.",
        examples=[[{"requirement_id": "advisor_reviewed_disclosure:SG_STRUCTURED_NOTE"}]],
    )
    consent_requirements: list[PolicyEvaluationRequirementProjection] = Field(
        description="Consent requirements that must stay visible through memo/report prep.",
        examples=[[{"requirement_id": "client_consent:SG_STRUCTURED_NOTE"}]],
    )
    conflict_posture: dict[str, Any] = Field(
        description="Conflict posture and blocker reason codes derived from policy rule outcomes.",
        examples=[{"status": "BLOCKED", "reason_codes": ["MATERIAL_CONFLICT_REQUIRES_REVIEW"]}],
    )
    sla_posture: dict[str, Any] = Field(
        description="Review queue age, open requirement count, and overdue posture.",
        examples=[{"status": "WITHIN_SLA", "open_requirement_count": 1}],
    )
    sign_off_status: PolicyEvaluationSignOffStatus = Field(
        description="Current sign-off readiness after applying requirement and event evidence.",
        examples=["PENDING_REVIEW"],
    )
    sign_off_blockers: list[str] = Field(
        default_factory=list,
        description="Blockers preventing policy sign-off or client-ready publication.",
        examples=[["DISCLOSURE_REQUIREMENT_OPEN:advisor_reviewed_disclosure:SG_STRUCTURED_NOTE"]],
    )
    maker_checker_required: bool = Field(
        description="Whether policy sign-off requires an actor different from record creator.",
        examples=[True],
    )
    latest_sign_off_event: PolicyEvaluationAuditEvent | None = Field(
        default=None,
        description="Latest append-only policy sign-off event where one exists.",
        examples=[{"event_type": "POLICY_EVALUATION_SIGN_OFF_RECORDED"}],
    )
    client_ready_publication: str = Field(
        description="Client-ready publication boundary for this policy workflow.",
        examples=["BLOCKED"],
    )


class PolicyEvaluationSignOffDecisionRequest(BaseModel):
    actor_id: str = Field(
        description="Actor recording the policy sign-off decision.",
        examples=["policy_checker_1"],
    )
    decision: PolicyEvaluationSignOffDecision = Field(
        description="Policy sign-off decision to record.",
        examples=["APPROVE_FOR_POLICY_SIGN_OFF"],
    )
    source_evaluation_hash: str = Field(
        description="Expected immutable policy evaluation hash reviewed by the decision actor.",
        examples=["sha256:policy-evaluation"],
    )
    resolved_approval_dependencies: list[str] = Field(
        default_factory=list,
        description="Approval dependencies resolved by this decision evidence.",
        examples=[["REVIEW_DISCLOSURE:SG_STRUCTURED_NOTE"]],
    )
    satisfied_disclosure_requirements: list[str] = Field(
        default_factory=list,
        description="Disclosure requirements satisfied by this decision evidence.",
        examples=[["advisor_reviewed_disclosure:SG_STRUCTURED_NOTE"]],
    )
    satisfied_consent_requirements: list[str] = Field(
        default_factory=list,
        description="Consent requirements satisfied by this decision evidence.",
        examples=[["client_consent:SG_STRUCTURED_NOTE"]],
    )
    conflict_review_outcome: str | None = Field(
        default=None,
        description="Conflict review outcome where conflict evidence was required.",
        examples=["NO_MATERIAL_CONFLICT_REMAINING"],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured sign-off rationale retained in append-only audit evidence.",
        examples=[{"purpose": "policy sign-off after disclosure and consent review"}],
    )


class PolicyEvaluationSignOffDecisionResponse(BaseModel):
    workflow: PolicyEvaluationWorkflowResponse = Field(
        description="Workflow posture after applying the sign-off decision."
    )
    sign_off_event: PolicyEvaluationAuditEvent = Field(
        description="Append-only sign-off or review event recorded for the decision."
    )
    replay_metadata: dict[str, Any] = Field(
        description="Hash and boundary metadata proving the decision source.",
        examples=[{"client_ready_publication": "BLOCKED"}],
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
