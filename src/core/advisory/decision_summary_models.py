from typing import Any, Literal

from pydantic import BaseModel, Field

ProposalDecisionStatus = Literal[
    "READY_FOR_CLIENT_REVIEW",
    "REQUIRES_RISK_REVIEW",
    "REQUIRES_COMPLIANCE_REVIEW",
    "REQUIRES_CLIENT_CONSENT",
    "BLOCKED_REMEDIATION_REQUIRED",
    "INSUFFICIENT_EVIDENCE",
    "REVISION_RECOMMENDED",
]

ProposalDecisionNextAction = Literal[
    "FIX_INPUT",
    "REVIEW_RISK",
    "REVIEW_COMPLIANCE",
    "DISCUSS_WITH_CLIENT",
    "APPROVE_AND_PROCEED",
    "REVISE_PROPOSAL",
    "COMPARE_ALTERNATIVES",
    "REQUEST_CLIENT_CONTEXT",
    "REQUEST_MANDATE_CONTEXT",
]

ProposalDecisionConfidence = Literal["HIGH", "MEDIUM", "LOW", "INSUFFICIENT"]


class ProposalDecisionApprovalRequirement(BaseModel):
    approval_type: Literal[
        "RISK_REVIEW",
        "COMPLIANCE_REVIEW",
        "CLIENT_CONSENT",
        "INVESTMENT_COUNSELLOR_REVIEW",
        "PRODUCT_SPECIALIST_REVIEW",
        "MANDATE_EXCEPTION_APPROVAL",
        "DATA_REMEDIATION",
    ] = Field(description="Approval or remediation type required by current decision posture.")
    required: bool = Field(description="Whether the requirement is currently active.")
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(description="Severity of the requirement.")
    reason_code: str = Field(description="Stable requirement reason code.")
    summary: str = Field(description="Advisor-facing explanation of the requirement.")
    blocking_until_approved: bool = Field(
        description="Whether this requirement blocks further progression."
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references supporting this requirement.",
    )
    policy_version: str = Field(description="Policy version used to derive this requirement.")


class ProposalDecisionMaterialChange(BaseModel):
    change_id: str = Field(description="Stable material change identifier.")
    family: Literal[
        "ALLOCATION_CHANGE",
        "CONCENTRATION_CHANGE",
        "CURRENCY_EXPOSURE_CHANGE",
        "LIQUIDITY_CHANGE",
        "CASH_CHANGE",
        "PRODUCT_COMPLEXITY_CHANGE",
        "RISK_PROFILE_ALIGNMENT_CHANGE",
        "MANDATE_ALIGNMENT_CHANGE",
        "APPROVAL_REQUIREMENT_CHANGE",
        "DATA_QUALITY_CHANGE",
    ] = Field(description="Material change family.")
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Severity assigned to this material change."
    )
    before: dict[str, Any] = Field(
        default_factory=dict,
        description="Before-state evidence snapshot for the change.",
    )
    after: dict[str, Any] = Field(
        default_factory=dict,
        description="After-state evidence snapshot for the change.",
    )
    delta: dict[str, Any] = Field(
        default_factory=dict,
        description="Normalized delta evidence for the change.",
    )
    threshold: dict[str, Any] = Field(
        default_factory=dict,
        description="Threshold metadata when applicable.",
    )
    summary: str = Field(description="Advisor-facing material change summary.")
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references supporting the material change.",
    )


class ProposalDecisionMissingEvidence(BaseModel):
    evidence_type: str = Field(description="Missing or unavailable evidence type.")
    reason_code: str = Field(description="Stable reason code for missing evidence.")
    summary: str = Field(description="Advisor-facing explanation of missing evidence.")
    blocking: bool = Field(
        description="Whether this missing evidence should be treated as blocking."
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references supporting the missing-evidence classification.",
    )


class ProposalDecisionActionItem(BaseModel):
    action_code: ProposalDecisionNextAction = Field(description="Recommended advisor action code.")
    reason_code: str = Field(description="Stable reason code for this action item.")
    summary: str = Field(description="Advisor-facing action summary.")
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references supporting the action item.",
    )


class ProposalDecisionSuitabilityPosture(BaseModel):
    status: Literal["AVAILABLE", "NOT_AVAILABLE"] = Field(
        description="Suitability posture availability."
    )
    issue_count_new: int = Field(description="Count of NEW suitability issues.")
    issue_count_resolved: int = Field(description="Count of RESOLVED suitability issues.")
    issue_count_persistent: int = Field(description="Count of PERSISTENT suitability issues.")
    highest_severity_new: Literal["LOW", "MEDIUM", "HIGH"] | None = Field(
        default=None,
        description="Highest severity among NEW issues.",
    )
    recommended_gate: Literal["NONE", "RISK_REVIEW", "COMPLIANCE_REVIEW"] | None = Field(
        default=None,
        description="Current suitability gate recommendation when available.",
    )


class ProposalDecisionRiskPosture(BaseModel):
    status: Literal["AVAILABLE", "UNAVAILABLE"] = Field(description="Risk posture availability.")
    source_service: str | None = Field(
        default=None,
        description="Risk authority service when available.",
    )
    summary: str = Field(description="Concise risk-posture explanation.")


class ProposalDecisionClientMandatePosture(BaseModel):
    status: Literal["NOT_EVALUATED", "PARTIAL", "AVAILABLE"] = Field(
        description="Current client and mandate posture availability."
    )
    summary: str = Field(description="Current client and mandate posture summary.")


class ProposalDecisionSummary(BaseModel):
    decision_status: ProposalDecisionStatus = Field(description="Richer decision outcome.")
    top_level_status: Literal["READY", "PENDING_REVIEW", "BLOCKED"] = Field(
        description="Existing coarse proposal status."
    )
    primary_reason_code: str = Field(description="Primary stable reason code.")
    primary_summary: str = Field(description="Primary advisor-facing decision summary.")
    recommended_next_action: ProposalDecisionNextAction = Field(
        description="Recommended advisor action."
    )
    decision_policy_version: str = Field(description="Decision policy version.")
    suitability_policy_version: str | None = Field(
        default=None,
        description="Suitability policy version when available.",
    )
    confidence: ProposalDecisionConfidence = Field(
        description="Confidence based on evidence completeness."
    )
    approval_requirements: list[ProposalDecisionApprovalRequirement] = Field(
        default_factory=list,
        description="Consolidated approval or remediation requirements.",
    )
    material_changes: list[ProposalDecisionMaterialChange] = Field(
        default_factory=list,
        description="Normalized material changes.",
    )
    suitability_posture: ProposalDecisionSuitabilityPosture | None = Field(
        default=None,
        description="Current suitability posture summary.",
    )
    missing_evidence: list[ProposalDecisionMissingEvidence] = Field(
        default_factory=list,
        description="Explicit missing-evidence items.",
    )
    risk_posture: ProposalDecisionRiskPosture | None = Field(
        default=None,
        description="Current risk-posture summary.",
    )
    client_and_mandate_posture: ProposalDecisionClientMandatePosture | None = Field(
        default=None,
        description="Current client and mandate posture summary.",
    )
    advisor_action_items: list[ProposalDecisionActionItem] = Field(
        default_factory=list,
        description="Advisor-facing action items.",
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references supporting this decision summary.",
    )
