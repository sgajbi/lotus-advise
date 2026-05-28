from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CopilotActionFamily = Literal[
    "PROPOSAL_EXPLANATION",
    "EVIDENCE_QA",
    "MEETING_PREPARATION",
    "COMPLIANCE_REVIEW_SUMMARY",
    "OPERATIONS_REPORT_HANDOFF",
    "CLIENT_FOLLOW_UP_DRAFT",
]

CopilotAudience = Literal[
    "ADVISOR",
    "DESK_HEAD",
    "COMPLIANCE_REVIEWER",
    "OPERATIONS_SUPPORT",
    "MODEL_RISK_OPERATOR",
]

CopilotSourceDependency = Literal[
    "RFC0023_PROPOSAL_NARRATIVE",
    "RFC0024_PROPOSAL_MEMO",
    "RFC0025_POLICY_EVALUATION",
    "RFC0026_ADVISOR_COCKPIT",
    "REPORT_READINESS",
    "OPERATIONS_HANDOFF",
]

CopilotEvidenceAccessClass = Literal[
    "ADVISOR_USE_SUMMARY",
    "COMPLIANCE_REVIEW_EVIDENCE",
    "OPERATIONS_HANDOFF_EVIDENCE",
    "MODEL_RISK_AUDIT",
    "INTERNAL_SUPPORTABILITY",
]

CopilotReviewPosture = Literal[
    "REVIEW_REQUIRED",
    "APPROVED_FOR_INTERNAL_USE",
    "REJECTED",
    "SUPERSEDED",
    "EXPIRED",
    "UNSUPPORTED",
    "GUARDRAIL_REJECTED",
    "UNAVAILABLE",
]

CopilotClientReadyPosture = Literal["BLOCKED"]

CopilotRetentionClass = Literal[
    "ADVISORY_REVIEW_RECORD",
    "MODEL_RISK_AUDIT",
    "SUPPORTABILITY_DIAGNOSTIC",
]

CopilotUnsupportedEvidenceReason = Literal[
    "SOURCE_NOT_IMPLEMENTED",
    "SOURCE_NOT_AVAILABLE",
    "RESTRICTED_BY_ROLE",
    "QUESTION_OUT_OF_SCOPE",
    "CLIENT_READY_PUBLICATION_BLOCKED",
    "POLICY_APPROVAL_NOT_AVAILABLE",
    "AI_UNAVAILABLE",
]


class CopilotActionDefinition(BaseModel):
    action_family: CopilotActionFamily = Field(
        description="Stable first-wave governed advisory copilot action family.",
        examples=["PROPOSAL_EXPLANATION"],
    )
    display_name: str = Field(
        description="Business-facing action name for advisor and reviewer surfaces.",
        examples=["Proposal explanation"],
    )
    business_purpose: str = Field(
        description="Private-banking business purpose for the bounded copilot action.",
        examples=["Explain proposal evidence for advisor review."],
    )
    supported_audiences: tuple[CopilotAudience, ...] = Field(
        description="Audiences allowed to request or review the action.",
        examples=[["ADVISOR", "DESK_HEAD"]],
    )
    required_source_dependencies: tuple[CopilotSourceDependency, ...] = Field(
        description="Implementation-backed sources required before the action can be supported.",
        examples=[["RFC0023_PROPOSAL_NARRATIVE", "RFC0024_PROPOSAL_MEMO"]],
    )
    output_evidence_classes: tuple[CopilotEvidenceAccessClass, ...] = Field(
        description="Evidence access classes produced or referenced by this action.",
        examples=[["ADVISOR_USE_SUMMARY"]],
    )
    workflow_pack_id: str = Field(
        description="Approved lotus-ai workflow-pack identifier reserved for this action family.",
        examples=["advisory_copilot_proposal_explanation.pack"],
    )
    workflow_pack_version: str = Field(
        default="v1",
        description="Workflow-pack version expected by first-wave copilot integration.",
        examples=["v1"],
    )
    workbench_surface_key: str = Field(
        description=(
            "Workbench surface key that may render this action after Gateway support exists."
        ),
        examples=["advisory_copilot.proposal_explanation"],
    )
    default_review_posture: CopilotReviewPosture = Field(
        default="REVIEW_REQUIRED",
        description="Default review posture for generated copilot output.",
        examples=["REVIEW_REQUIRED"],
    )
    client_ready_publication: CopilotClientReadyPosture = Field(
        default="BLOCKED",
        description="Client-ready publication posture for all first-wave copilot output.",
        examples=["BLOCKED"],
    )


class CopilotBusinessProjection(BaseModel):
    action_family: CopilotActionFamily = Field(
        description="Action family represented by the business-facing projection.",
        examples=["MEETING_PREPARATION"],
    )
    label: str = Field(
        description="Business-facing label safe for advisor and reviewer surfaces.",
        examples=["Meeting preparation"],
    )
    summary: str = Field(
        description="Business-facing summary safe for UI, report, wiki, and commercial copy.",
        examples=["Prepare an advisor-reviewed meeting note from source-backed evidence."],
    )
    next_action_label: str = Field(
        description="Business-facing next action label that does not expose technical internals.",
        examples=["Review draft"],
    )


class CopilotSourceRef(BaseModel):
    source_system: str = Field(
        description="Authoritative Lotus system that owns the cited evidence.",
        examples=["lotus-advise"],
    )
    source_type: str = Field(
        description="Evidence family emitted by the source authority.",
        examples=["POLICY_EVALUATION"],
    )
    source_id: str = Field(
        description="Stable source evidence identifier safe for audit use.",
        examples=["policy_eval_sg_001"],
    )
    content_hash: str | None = Field(
        default=None,
        description="Source content hash when the source authority exposes one.",
        examples=["sha256:policy-evaluation"],
    )
    access_class: CopilotEvidenceAccessClass = Field(
        description="Projection and access class for this evidence ref.",
        examples=["COMPLIANCE_REVIEW_EVIDENCE"],
    )


class CopilotLineageRef(BaseModel):
    lineage_type: str = Field(
        description="Lineage reference family, such as evidence packet, workflow run, or review.",
        examples=["EVIDENCE_PACKET"],
    )
    lineage_id: str = Field(
        description="Stable lineage reference identifier.",
        examples=["copilot_packet_pb_sg_001"],
    )
    source_system: str = Field(
        description="System that owns the lineage reference.",
        examples=["lotus-advise"],
    )


class CopilotUnsupportedEvidence(BaseModel):
    reason_code: CopilotUnsupportedEvidenceReason = Field(
        description="Stable reason code for unsupported or unavailable evidence.",
        examples=["SOURCE_NOT_AVAILABLE"],
    )
    source_dependency: CopilotSourceDependency | None = Field(
        default=None,
        description="Source dependency that prevented support when applicable.",
        examples=["RFC0025_POLICY_EVALUATION"],
    )
    advisor_message: str = Field(
        description="Business-facing explanation that avoids technical internals.",
        examples=["Policy evidence is not available for this request."],
    )


class CopilotEvidencePacketSection(BaseModel):
    section_key: str = Field(
        description="Stable evidence section key included in the packet.",
        examples=["POLICY_POSTURE"],
    )
    title: str = Field(
        description="Business-facing section title.",
        examples=["Policy posture"],
    )
    evidence_class: CopilotEvidenceAccessClass = Field(
        description="Access class for this evidence section.",
        examples=["COMPLIANCE_REVIEW_EVIDENCE"],
    )
    source_refs: tuple[CopilotSourceRef, ...] = Field(
        description="Source refs used to build this evidence section.",
    )
    summary_items: tuple[str, ...] = Field(
        default=(),
        description="Business-safe evidence statements allowed for the requested projection.",
        examples=[["Policy evaluation requires compliance review."]],
    )


class CopilotEvidenceSectionInput(BaseModel):
    section_key: str = Field(
        description="Stable evidence section key offered by the source projection.",
        examples=["POLICY_POSTURE"],
    )
    title: str = Field(
        description="Business-facing section title.",
        examples=["Policy posture"],
    )
    evidence_class: CopilotEvidenceAccessClass = Field(
        description="Access class for this source section.",
        examples=["COMPLIANCE_REVIEW_EVIDENCE"],
    )
    source_refs: tuple[CopilotSourceRef, ...] = Field(
        description="Source refs used to build this evidence section.",
    )
    summary_items: tuple[str, ...] = Field(
        description="Business-safe evidence statements emitted by the source projection.",
        examples=[["Policy evaluation requires compliance review."]],
    )
    allowed_audiences: tuple[CopilotAudience, ...] = Field(
        description="Audiences allowed to receive this evidence section.",
        examples=[["ADVISOR", "COMPLIANCE_REVIEWER"]],
    )


class CopilotEvidencePacket(BaseModel):
    evidence_packet_id: str = Field(
        description="Stable evidence-packet identifier for copilot action execution.",
        examples=["copilot_packet_pb_sg_001"],
    )
    evidence_packet_hash: str = Field(
        description="Deterministic hash of projected packet content and source refs.",
        examples=["sha256:copilot-packet"],
    )
    action_family: CopilotActionFamily = Field(
        description="Copilot action family this packet supports.",
        examples=["COMPLIANCE_REVIEW_SUMMARY"],
    )
    portfolio_id: str = Field(
        description="Portfolio identifier for source-scoped advisory evidence.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    proposal_id: str | None = Field(
        default=None,
        description="Proposal identifier when the copilot action is proposal-scoped.",
        examples=["proposal_sg_structured_note_001"],
    )
    sections: tuple[CopilotEvidencePacketSection, ...] = Field(
        description="Redacted, source-backed evidence sections allowed for the action.",
    )
    unsupported_evidence: tuple[CopilotUnsupportedEvidence, ...] = Field(
        default=(),
        description="Controlled unsupported-evidence posture for missing or restricted sources.",
    )
    lineage_refs: tuple[CopilotLineageRef, ...] = Field(
        default=(),
        description="Lineage refs for packet, source, workflow, review, and audit evidence.",
    )
    retention_class: CopilotRetentionClass = Field(
        description="Retention class for evidence-packet handling.",
        examples=["ADVISORY_REVIEW_RECORD"],
    )
    client_ready_publication: CopilotClientReadyPosture = Field(
        default="BLOCKED",
        description="Client-ready publication posture for evidence produced by this packet.",
        examples=["BLOCKED"],
    )
