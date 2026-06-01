from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, Field, field_validator

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

_COPILOT_SOURCE_SYSTEM_MAX_LENGTH = 64
_COPILOT_SOURCE_TYPE_MAX_LENGTH = 96
_COPILOT_SOURCE_ID_MAX_LENGTH = 160
_COPILOT_CONTENT_HASH_MAX_LENGTH = 128
_COPILOT_SECTION_KEY_MAX_LENGTH = 96
_COPILOT_SECTION_TITLE_MAX_LENGTH = 160
_COPILOT_SUMMARY_ITEM_LIMIT = 8
_COPILOT_SUMMARY_ITEM_MAX_LENGTH = 1000
_COPILOT_SOURCE_REF_LIMIT = 8
_COPILOT_IDENTIFIER_MAX_LENGTH = 160
_COPILOT_HASH_MAX_LENGTH = 128
_COPILOT_LINEAGE_TYPE_MAX_LENGTH = 96
_COPILOT_LINEAGE_REF_LIMIT = 16
_COPILOT_UNSUPPORTED_EVIDENCE_LIMIT = 12
_COPILOT_UNSUPPORTED_MESSAGE_MAX_LENGTH = 500
_COPILOT_BUSINESS_COPY_TECHNICAL_TERMS = (
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
    "api key",
    "apikey",
    "raw prompt",
    "provider response",
    "provider output",
    "trace id",
    "correlation id",
    "run ledger",
    "raw payload",
    "raw source",
)
COPILOT_AUDIENCE_LIMIT = 5
COPILOT_PACKET_SECTION_LIMIT = 12


class CopilotActionDefinition(BaseModel):
    action_family: CopilotActionFamily = Field(
        description="Stable supported governed advisory copilot action family.",
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
        min_length=1,
        max_length=COPILOT_AUDIENCE_LIMIT,
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
        description="Workflow-pack version expected by supported copilot integration.",
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
        description="Client-ready publication posture for all supported copilot output.",
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

    @field_validator("label", "summary", "next_action_label")
    @classmethod
    def _business_copy_must_be_safe(cls, value: str) -> str:
        normalized = _normalize_required_text(
            value,
            error_code="COPILOT_BUSINESS_PROJECTION_REQUIRED",
        )
        assert_copilot_business_safe_text(normalized)
        return normalized


class CopilotSourceRef(BaseModel):
    source_system: str = Field(
        description="Authoritative Lotus system that owns the cited evidence.",
        examples=["lotus-advise"],
        min_length=1,
        max_length=_COPILOT_SOURCE_SYSTEM_MAX_LENGTH,
    )
    source_type: str = Field(
        description="Evidence family emitted by the source authority.",
        examples=["POLICY_EVALUATION"],
        min_length=1,
        max_length=_COPILOT_SOURCE_TYPE_MAX_LENGTH,
    )
    source_id: str = Field(
        description="Stable source evidence identifier safe for audit use.",
        examples=["policy_eval_sg_001"],
        min_length=1,
        max_length=_COPILOT_SOURCE_ID_MAX_LENGTH,
    )
    content_hash: str | None = Field(
        default=None,
        description="Source content hash when the source authority exposes one.",
        examples=["sha256:policy-evaluation"],
        min_length=1,
        max_length=_COPILOT_CONTENT_HASH_MAX_LENGTH,
    )
    access_class: CopilotEvidenceAccessClass = Field(
        description="Projection and access class for this evidence ref.",
        examples=["COMPLIANCE_REVIEW_EVIDENCE"],
    )

    @field_validator("source_system", "source_type", "source_id")
    @classmethod
    def _normalize_required_ref_text(cls, value: str) -> str:
        return _normalize_required_text(value, error_code="COPILOT_SOURCE_REF_REQUIRED")

    @field_validator("content_hash")
    @classmethod
    def _normalize_optional_ref_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_required_text(value, error_code="COPILOT_SOURCE_REF_REQUIRED")


class CopilotLineageRef(BaseModel):
    lineage_type: str = Field(
        description="Lineage reference family, such as evidence packet, workflow run, or review.",
        examples=["EVIDENCE_PACKET"],
        min_length=1,
        max_length=_COPILOT_LINEAGE_TYPE_MAX_LENGTH,
    )
    lineage_id: str = Field(
        description="Stable lineage reference identifier.",
        examples=["copilot_packet_pb_sg_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    source_system: str = Field(
        description="System that owns the lineage reference.",
        examples=["lotus-advise"],
        min_length=1,
        max_length=_COPILOT_SOURCE_SYSTEM_MAX_LENGTH,
    )

    @field_validator("lineage_type", "lineage_id", "source_system")
    @classmethod
    def _normalize_required_lineage_text(cls, value: str) -> str:
        return _normalize_required_text(value, error_code="COPILOT_LINEAGE_REF_REQUIRED")


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
        min_length=1,
        max_length=_COPILOT_UNSUPPORTED_MESSAGE_MAX_LENGTH,
    )

    @field_validator("advisor_message")
    @classmethod
    def _normalize_advisor_message(cls, value: str) -> str:
        normalized = _normalize_required_text(
            value,
            error_code="COPILOT_UNSUPPORTED_MESSAGE_REQUIRED",
        )
        if contains_copilot_business_technical_detail(normalized):
            raise ValueError("COPILOT_UNSUPPORTED_MESSAGE_TECHNICAL_DETAIL")
        return normalized


class CopilotEvidencePacketSection(BaseModel):
    section_key: str = Field(
        description="Stable evidence section key included in the packet.",
        examples=["POLICY_POSTURE"],
        min_length=1,
        max_length=_COPILOT_SECTION_KEY_MAX_LENGTH,
    )
    title: str = Field(
        description="Business-facing section title.",
        examples=["Policy posture"],
        min_length=1,
        max_length=_COPILOT_SECTION_TITLE_MAX_LENGTH,
    )
    evidence_class: CopilotEvidenceAccessClass = Field(
        description="Access class for this evidence section.",
        examples=["COMPLIANCE_REVIEW_EVIDENCE"],
    )
    source_refs: tuple[CopilotSourceRef, ...] = Field(
        description="Source refs used to build this evidence section.",
        min_length=1,
        max_length=_COPILOT_SOURCE_REF_LIMIT,
    )
    summary_items: tuple[str, ...] = Field(
        default=(),
        description="Business-safe evidence statements allowed for the requested projection.",
        examples=[["Policy evaluation requires compliance review."]],
        max_length=_COPILOT_SUMMARY_ITEM_LIMIT,
    )

    @field_validator("section_key", "title")
    @classmethod
    def _normalize_required_section_text(cls, value: str) -> str:
        normalized = _normalize_required_text(
            value,
            error_code="COPILOT_EVIDENCE_SECTION_REQUIRED",
        )
        if contains_copilot_business_technical_detail(normalized):
            raise ValueError("COPILOT_EVIDENCE_TEXT_LEAKS_TECHNICAL_DETAIL")
        return normalized

    @field_validator("summary_items", mode="before")
    @classmethod
    def _normalize_summary_items(cls, value: Any) -> tuple[str, ...]:
        return _normalize_summary_tuple(value, allow_empty=True)


class CopilotEvidenceSectionInput(BaseModel):
    section_key: str = Field(
        description="Stable evidence section key offered by the source projection.",
        examples=["POLICY_POSTURE"],
        min_length=1,
        max_length=_COPILOT_SECTION_KEY_MAX_LENGTH,
    )
    title: str = Field(
        description="Business-facing section title.",
        examples=["Policy posture"],
        min_length=1,
        max_length=_COPILOT_SECTION_TITLE_MAX_LENGTH,
    )
    evidence_class: CopilotEvidenceAccessClass = Field(
        description="Access class for this source section.",
        examples=["COMPLIANCE_REVIEW_EVIDENCE"],
    )
    source_refs: tuple[CopilotSourceRef, ...] = Field(
        description="Source refs used to build this evidence section.",
        min_length=1,
        max_length=_COPILOT_SOURCE_REF_LIMIT,
    )
    summary_items: tuple[str, ...] = Field(
        description="Business-safe evidence statements emitted by the source projection.",
        examples=[["Policy evaluation requires compliance review."]],
        min_length=1,
        max_length=_COPILOT_SUMMARY_ITEM_LIMIT,
    )
    allowed_audiences: tuple[CopilotAudience, ...] = Field(
        description="Audiences allowed to receive this evidence section.",
        examples=[["ADVISOR", "COMPLIANCE_REVIEWER"]],
        min_length=1,
        max_length=COPILOT_AUDIENCE_LIMIT,
    )

    @field_validator("section_key", "title")
    @classmethod
    def _normalize_required_section_text(cls, value: str) -> str:
        normalized = _normalize_required_text(
            value,
            error_code="COPILOT_EVIDENCE_SECTION_REQUIRED",
        )
        if contains_copilot_business_technical_detail(normalized):
            raise ValueError("COPILOT_EVIDENCE_TEXT_LEAKS_TECHNICAL_DETAIL")
        return normalized

    @field_validator("summary_items", mode="before")
    @classmethod
    def _normalize_summary_items(cls, value: Any) -> tuple[str, ...]:
        return _normalize_summary_tuple(value, allow_empty=False)

    @field_validator("allowed_audiences", mode="before")
    @classmethod
    def _normalize_allowed_audiences(cls, value: Any) -> tuple[CopilotAudience, ...]:
        return _normalize_audience_tuple(value)


class CopilotEvidencePacket(BaseModel):
    evidence_packet_id: str = Field(
        description="Stable evidence-packet identifier for copilot action execution.",
        examples=["copilot_packet_pb_sg_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    evidence_packet_hash: str = Field(
        description="Deterministic hash of projected packet content and source refs.",
        examples=["sha256:copilot-packet"],
        min_length=1,
        max_length=_COPILOT_HASH_MAX_LENGTH,
    )
    action_family: CopilotActionFamily = Field(
        description="Copilot action family this packet supports.",
        examples=["COMPLIANCE_REVIEW_SUMMARY"],
    )
    portfolio_id: str = Field(
        description="Portfolio identifier for source-scoped advisory evidence.",
        examples=["PB_SG_GLOBAL_BAL_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    proposal_id: str | None = Field(
        default=None,
        description="Proposal identifier when the copilot action is proposal-scoped.",
        examples=["proposal_sg_structured_note_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    sections: tuple[CopilotEvidencePacketSection, ...] = Field(
        description="Redacted, source-backed evidence sections allowed for the action.",
        max_length=COPILOT_PACKET_SECTION_LIMIT,
    )
    unsupported_evidence: tuple[CopilotUnsupportedEvidence, ...] = Field(
        default=(),
        description="Controlled unsupported-evidence posture for missing or restricted sources.",
        max_length=_COPILOT_UNSUPPORTED_EVIDENCE_LIMIT,
    )
    lineage_refs: tuple[CopilotLineageRef, ...] = Field(
        default=(),
        description="Lineage refs for packet, source, workflow, review, and audit evidence.",
        max_length=_COPILOT_LINEAGE_REF_LIMIT,
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

    @field_validator("evidence_packet_id", "evidence_packet_hash", "portfolio_id")
    @classmethod
    def _normalize_required_packet_text(cls, value: str) -> str:
        return _normalize_required_text(value, error_code="COPILOT_EVIDENCE_PACKET_REQUIRED")

    @field_validator("proposal_id")
    @classmethod
    def _normalize_optional_packet_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_required_text(value, error_code="COPILOT_EVIDENCE_PACKET_REQUIRED")


def _normalize_required_text(value: str, *, error_code: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(error_code)
    return normalized


def _normalize_summary_tuple(value: Any, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("COPILOT_EVIDENCE_SUMMARY_INVALID")

    normalized: list[str] = []
    for item in value:
        if len(normalized) >= _COPILOT_SUMMARY_ITEM_LIMIT:
            raise ValueError("COPILOT_EVIDENCE_SUMMARY_TOO_LARGE")
        if not isinstance(item, str):
            raise ValueError("COPILOT_EVIDENCE_SUMMARY_INVALID")
        summary = _normalize_required_text(
            item,
            error_code="COPILOT_EVIDENCE_SUMMARY_REQUIRED",
        )
        if len(summary) > _COPILOT_SUMMARY_ITEM_MAX_LENGTH:
            raise ValueError("COPILOT_EVIDENCE_SUMMARY_TOO_LARGE")
        if contains_copilot_business_technical_detail(summary):
            raise ValueError("COPILOT_EVIDENCE_TEXT_LEAKS_TECHNICAL_DETAIL")
        normalized.append(summary)

    if not normalized and not allow_empty:
        raise ValueError("COPILOT_EVIDENCE_SUMMARY_REQUIRED")
    return tuple(normalized)


def _normalize_audience_tuple(value: Any) -> tuple[CopilotAudience, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("COPILOT_AUDIENCE_INVALID")

    allowed = {
        "ADVISOR",
        "DESK_HEAD",
        "COMPLIANCE_REVIEWER",
        "OPERATIONS_SUPPORT",
        "MODEL_RISK_OPERATOR",
    }
    normalized: list[CopilotAudience] = []
    for item in value:
        if len(normalized) >= COPILOT_AUDIENCE_LIMIT:
            raise ValueError("COPILOT_AUDIENCE_TOO_LARGE")
        if not isinstance(item, str):
            raise ValueError("COPILOT_AUDIENCE_INVALID")
        audience = item.strip()
        if audience not in allowed:
            raise ValueError("COPILOT_AUDIENCE_INVALID")
        if audience not in normalized:
            normalized.append(cast(CopilotAudience, audience))

    if not normalized:
        raise ValueError("COPILOT_AUDIENCE_REQUIRED")
    return tuple(normalized)


def assert_copilot_business_safe_text(*values: str) -> None:
    if contains_copilot_business_technical_detail(" ".join(values)):
        raise ValueError("COPILOT_EVIDENCE_TEXT_LEAKS_TECHNICAL_DETAIL")


def contains_copilot_business_technical_detail(value: str) -> bool:
    normalized = value.lower().replace("-", " ").replace("_", " ")
    return any(term in normalized for term in _COPILOT_BUSINESS_COPY_TECHNICAL_TERMS)
