from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.core.policy_packs.evaluation_models import PolicyEvaluationStatus
from src.core.policy_packs.persistence_models import PolicyEvaluationAuditEvent

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
