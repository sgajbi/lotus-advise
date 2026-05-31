from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

AdvisorCockpitActionStatus = Literal[
    "READY",
    "PENDING_REVIEW",
    "BLOCKED",
    "ACKNOWLEDGED",
    "HANDOFF_REQUESTED",
    "COMPLETED",
    "SUPERSEDED",
]
AdvisorCockpitActionPriority = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]
AdvisorCockpitOwnerRole = Literal[
    "ADVISOR",
    "DESK_HEAD",
    "COMPLIANCE_REVIEWER",
    "INVESTMENT_DESK",
    "PORTFOLIO_MANAGER",
    "OPERATIONS",
    "CRM_OWNER",
    "REPORTING_OWNER",
    "ARCHIVE_OWNER",
    "EXECUTION_OWNER",
    "SYSTEM",
]
AdvisorCockpitCallerRole = Literal[
    "ADVISOR",
    "DESK_HEAD",
    "COMPLIANCE_REVIEWER",
    "INVESTMENT_DESK",
    "PORTFOLIO_MANAGER",
    "OPERATIONS",
    "CRM_OWNER",
    "REPORTING_OWNER",
    "ARCHIVE_OWNER",
    "EXECUTION_OWNER",
    "DPM_OWNER",
    "SYSTEM",
]
AdvisorCockpitSlaAgeBand = Literal[
    "NOT_DUE",
    "DUE_SOON",
    "DUE_NOW",
    "OVERDUE",
    "CRITICAL_OVERDUE",
    "NOT_APPLICABLE",
]
AdvisorCockpitActionFamily = Literal[
    "CLIENT_MEETING_PREPARATION",
    "PROPOSAL_READY_FOR_REVIEW",
    "PROPOSAL_BLOCKED_BY_SOURCE_GAP",
    "POLICY_REVIEW_REQUIRED",
    "APPROVAL_DEPENDENCY_AGING",
    "CLIENT_CONSENT_REQUIRED",
    "MEMO_PACKAGE_BLOCKED",
    "REPORT_RENDER_ARCHIVE_BLOCKED",
    "EXECUTION_HANDOFF_READY",
    "EXECUTION_STATUS_ATTENTION",
    "HOUSE_VIEW_IMPACT_REVIEW",
    "WORKSPACE_DRAFT_STALE",
    "CLIENT_FOLLOW_UP_REQUIRED",
    "SUPPORTABILITY_DEGRADED",
    "UNSUPPORTED_CAPABILITY",
]
CockpitEvidenceAccessClass = Literal[
    "CUSTOMER_CONSUMABLE_SUMMARY",
    "RESTRICTED_CUSTOMER_EVIDENCE",
    "OPERATOR_ONLY_SUPPORTABILITY",
    "INTERNAL_ONLY_DIAGNOSTICS",
]
CockpitDependencyState = Literal["READY", "DEGRADED", "UNAVAILABLE", "NOT_CONFIGURED"]
AdvisorCockpitUnsupportedCapability = Literal[
    "CLIENT_READY_PUBLICATION",
    "EXTERNAL_CLIENT_COMMUNICATION",
    "CRM_SYSTEM_OF_RECORD",
    "CALENDAR_SCHEDULING",
    "OMS_ORDER_LIFECYCLE",
    "COMPLETED_POLICY_APPROVAL_AUTHORITY",
    "COMPLETED_POLICY_SIGN_OFF_AUTHORITY",
    "FULL_RFC0028_DEMO_RFP_PACKAGE",
]
_COCKPIT_IDENTIFIER_MAX_LENGTH = 160
_COCKPIT_TEXT_MAX_LENGTH = 1000
_COCKPIT_SUMMARY_MAX_LENGTH = 512
_COCKPIT_LIST_MAX_ITEMS = 64
_COCKPIT_PREPARATION_SECTIONS_MAX_ITEMS = 32
_COCKPIT_SUPPORTABILITY_KEYS_MAX_ITEMS = 64
_COCKPIT_SENSITIVE_TERMS = (
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
    "api key",
    "apikey",
    "raw prompt",
    "raw payload",
    "provider response",
)
_COCKPIT_OWNER_ROLE_LABELS = {
    "ADVISOR": "Advisor",
    "DESK_HEAD": "Desk head",
    "COMPLIANCE_REVIEWER": "Compliance reviewer",
    "INVESTMENT_DESK": "Investment desk",
    "PORTFOLIO_MANAGER": "Portfolio manager",
    "OPERATIONS": "Operations",
    "CRM_OWNER": "Client-relationship owner",
    "REPORTING_OWNER": "Reporting owner",
    "ARCHIVE_OWNER": "Archive owner",
    "EXECUTION_OWNER": "Execution owner",
    "SYSTEM": "System",
}


def cockpit_owner_role_label(role: str) -> str:
    return _COCKPIT_OWNER_ROLE_LABELS.get(role, role.replace("_", " ").title())


class CockpitCallerContext(BaseModel):
    advisor_id: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Advisor identifier for advisor-scoped cockpit reads.",
        examples=["advisor_sg_001"],
    )
    desk_id: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Desk identifier for desk-head or supervisory cockpit reads.",
        examples=["sg_private_bank_desk"],
    )
    coverage_team_id: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Coverage-team identifier when a source-backed assignment exists.",
        examples=["coverage_team_sg_01"],
    )
    role: AdvisorCockpitCallerRole = Field(
        description="Caller role used for server-side entitlement projection.",
        examples=["ADVISOR"],
    )
    demo_context: bool = Field(
        default=False,
        description="Whether the caller is using governed synthetic demo data.",
        examples=[True],
    )

    @field_validator("advisor_id", "desk_id", "coverage_team_id")
    @classmethod
    def _caller_refs_must_be_bounded(cls, value: str | None) -> str | None:
        return _normalize_optional_identifier(value, field_name="caller context")


class CockpitEvidenceRef(BaseModel):
    evidence_id: str = Field(
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Stable evidence identifier emitted by the source authority.",
        examples=["policy_eval_sg_001"],
    )
    evidence_type: str = Field(
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Evidence family, such as policy evaluation, memo, report, or supportability.",
        examples=["POLICY_EVALUATION"],
    )
    source_system: str = Field(
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Authoritative Lotus system that owns the evidence.",
        examples=["lotus-advise"],
    )
    access_class: CockpitEvidenceAccessClass = Field(
        description="Access class for projection and documentation controls.",
        examples=["RESTRICTED_CUSTOMER_EVIDENCE"],
    )
    summary: str = Field(
        max_length=_COCKPIT_SUMMARY_MAX_LENGTH,
        description="Support-safe evidence summary for advisor cockpit display.",
        examples=["Policy evaluation requires compliance review."],
    )

    @field_validator("evidence_id", "evidence_type", "source_system")
    @classmethod
    def _evidence_refs_must_be_bounded(cls, value: str) -> str:
        return _normalize_required_identifier(value, field_name="cockpit evidence reference")

    @field_validator("summary")
    @classmethod
    def _evidence_summary_must_be_business_safe(cls, value: str) -> str:
        return _normalize_business_text(value, field_name="cockpit evidence summary")


class CockpitLineageRef(BaseModel):
    lineage_id: str = Field(
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Stable lineage reference for audit and replay.",
        examples=["lineage_policy_eval_sg_001"],
    )
    source_system: str = Field(
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="System that produced the lineage reference.",
        examples=["lotus-advise"],
    )
    content_hash: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Optional canonical hash for immutable source evidence.",
        examples=["sha256:policy-evaluation"],
    )

    @field_validator("lineage_id", "source_system")
    @classmethod
    def _lineage_refs_must_be_bounded(cls, value: str) -> str:
        return _normalize_required_identifier(value, field_name="cockpit lineage reference")

    @field_validator("content_hash")
    @classmethod
    def _content_hash_must_be_bounded(cls, value: str | None) -> str | None:
        return _normalize_optional_identifier(value, field_name="cockpit lineage hash")


class CockpitSourceReadinessGap(BaseModel):
    source_family: str = Field(
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Source family with missing, stale, degraded, or unsupported evidence.",
        examples=["policy"],
    )
    gap_code: str = Field(
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Machine-readable source readiness gap code.",
        examples=["POLICY_REVIEW_PENDING"],
    )
    owner_role: AdvisorCockpitOwnerRole = Field(
        description="Role expected to resolve or own the gap.",
        examples=["COMPLIANCE_REVIEWER"],
    )
    message: str = Field(
        max_length=_COCKPIT_SUMMARY_MAX_LENGTH,
        description="Business-facing support-safe explanation of the source gap.",
        examples=["Policy review is pending before client-ready posture can change."],
    )

    @field_validator("source_family", "gap_code")
    @classmethod
    def _source_gap_refs_must_be_bounded(cls, value: str) -> str:
        return _normalize_required_identifier(value, field_name="cockpit source gap reference")

    @field_validator("message")
    @classmethod
    def _source_gap_message_must_be_business_safe(cls, value: str) -> str:
        return _normalize_business_text(value, field_name="cockpit source gap message")


class CockpitDependencyReadiness(BaseModel):
    dependency: str = Field(
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Dependency or source family name.",
        examples=["lotus-report"],
    )
    state: CockpitDependencyState = Field(
        description="Dependency readiness posture.",
        examples=["DEGRADED"],
    )
    reason_code: str = Field(
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Bounded machine-readable readiness reason.",
        examples=["REPORT_PACKAGE_UNAVAILABLE"],
    )
    summary: str = Field(
        max_length=_COCKPIT_SUMMARY_MAX_LENGTH,
        description="Support-safe dependency readiness summary.",
        examples=["Report package status is degraded; advisor action remains blocked."],
    )

    @field_validator("dependency", "reason_code")
    @classmethod
    def _dependency_refs_must_be_bounded(cls, value: str) -> str:
        return _normalize_required_identifier(value, field_name="cockpit dependency reference")

    @field_validator("summary")
    @classmethod
    def _dependency_summary_must_be_business_safe(cls, value: str) -> str:
        return _normalize_business_text(value, field_name="cockpit dependency summary")


class CockpitAcknowledgementState(BaseModel):
    acknowledged: bool = Field(
        description="Whether an advisory-owned action has been acknowledged.",
        examples=[False],
    )
    acknowledgement_id: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Append-only acknowledgement identifier when present.",
        examples=["ack_001"],
    )
    acknowledged_by: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Actor that acknowledged the action item.",
        examples=["advisor_sg_001"],
    )
    acknowledged_at: str | None = Field(
        default=None,
        description="UTC ISO8601 acknowledgement timestamp.",
        examples=["2026-05-27T08:00:00+00:00"],
    )
    acknowledgement_note: str | None = Field(
        default=None,
        max_length=_COCKPIT_SUMMARY_MAX_LENGTH,
        description="Support-safe acknowledgement note.",
        examples=["Advisor has reviewed the pending compliance action."],
    )

    @field_validator("acknowledgement_id", "acknowledged_by", "acknowledged_at")
    @classmethod
    def _ack_refs_must_be_bounded(cls, value: str | None) -> str | None:
        return _normalize_optional_identifier(value, field_name="cockpit acknowledgement")

    @field_validator("acknowledgement_note")
    @classmethod
    def _ack_note_must_be_business_safe(cls, value: str | None) -> str | None:
        return _normalize_optional_business_text(value, field_name="cockpit acknowledgement note")

    @model_validator(mode="after")
    def _acknowledgement_fields_must_match_state(self) -> CockpitAcknowledgementState:
        if not self.acknowledged:
            supplied = (
                self.acknowledgement_id,
                self.acknowledged_by,
                self.acknowledged_at,
                self.acknowledgement_note,
            )
            if any(value is not None for value in supplied):
                raise ValueError("unacknowledged cockpit state cannot carry acknowledgement detail")
        return self


class AdvisoryActionItem(BaseModel):
    action_item_id: str = Field(
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Stable advisory action item identifier.",
        examples=["aci_policy_review_001"],
    )
    action_item_version: int = Field(
        description="Monotonic action-item version used for stale acknowledgement checks.",
        examples=[1],
    )
    action_family: AdvisorCockpitActionFamily = Field(
        description="Business action family owned by the cockpit domain.",
        examples=["POLICY_REVIEW_REQUIRED"],
    )
    status: AdvisorCockpitActionStatus = Field(
        description="Current action posture.",
        examples=["PENDING_REVIEW"],
    )
    priority: AdvisorCockpitActionPriority = Field(
        description="Backend-owned deterministic priority.",
        examples=["HIGH"],
    )
    owner_role: AdvisorCockpitOwnerRole = Field(
        description=(
            "Machine-readable role that owns the next step or external handoff. "
            "Use owner_role_label for business-facing display."
        ),
        examples=["COMPLIANCE_REVIEWER"],
    )
    owner_role_label: str = Field(
        default="",
        max_length=_COCKPIT_SUMMARY_MAX_LENGTH,
        description="Business-facing owner label for advisor cockpit display.",
        examples=["Compliance reviewer"],
    )
    owning_system: str = Field(
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="System of record for the current action state.",
        examples=["lotus-advise"],
    )
    title: str = Field(
        max_length=_COCKPIT_SUMMARY_MAX_LENGTH,
        description="Business-facing action title.",
        examples=["Policy review required"],
    )
    next_required_action: str = Field(
        max_length=_COCKPIT_TEXT_MAX_LENGTH,
        description="Backend-owned next action; Workbench must render, not infer.",
        examples=["Review policy evaluation before advisor follow-up."],
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        max_length=_COCKPIT_LIST_MAX_ITEMS,
        description="Deterministic reason codes explaining status and priority.",
        examples=[["POLICY_PENDING_REVIEW", "CLIENT_READY_BLOCKED"]],
    )
    client_ref: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Source-backed client reference.",
    )
    household_ref: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Source-backed household reference when available.",
    )
    portfolio_id: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Source-backed portfolio identifier.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    proposal_id: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Source-backed proposal identifier.",
    )
    workspace_id: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Source-backed workspace id.",
    )
    memo_id: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Source-backed memo id.",
    )
    policy_evaluation_id: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Source-backed policy evaluation id.",
        examples=["policy_eval_sg_001"],
    )
    report_ref: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Source-backed report reference.",
    )
    execution_ref: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Source-backed execution handoff/status reference.",
    )
    due_at: str | None = Field(
        default=None,
        description="UTC ISO8601 due timestamp when the action has an SLA.",
        examples=["2026-05-28T08:00:00+00:00"],
    )
    sla_age_band: AdvisorCockpitSlaAgeBand = Field(
        description="Backend-owned SLA aging posture.",
        examples=["DUE_SOON"],
    )
    materiality_rank: int = Field(
        default=0,
        ge=0,
        description="Bounded materiality rank used only as a deterministic tie-breaker.",
        examples=[20],
    )
    source_timestamp: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="UTC ISO8601 timestamp for the source event or evidence that created action.",
        examples=["2026-05-27T07:30:00+00:00"],
    )
    evidence_refs: list[CockpitEvidenceRef] = Field(
        default_factory=list,
        max_length=_COCKPIT_LIST_MAX_ITEMS,
        description="Source-owned evidence references that justify the action.",
    )
    source_readiness_gaps: list[CockpitSourceReadinessGap] = Field(
        default_factory=list,
        max_length=_COCKPIT_LIST_MAX_ITEMS,
        description="Missing, stale, degraded, or unsupported source evidence gaps.",
    )
    dependency_readiness: list[CockpitDependencyReadiness] = Field(
        default_factory=list,
        max_length=_COCKPIT_LIST_MAX_ITEMS,
        description="Dependency readiness posture relevant to the action.",
    )
    lineage_refs: list[CockpitLineageRef] = Field(
        default_factory=list,
        max_length=_COCKPIT_LIST_MAX_ITEMS,
        description="Lineage references for audit and replay.",
    )
    acknowledgement_state: CockpitAcknowledgementState = Field(
        default_factory=lambda: CockpitAcknowledgementState(acknowledged=False),
        description="Advisory-owned acknowledgement posture.",
    )
    unsupported_capabilities: list[AdvisorCockpitUnsupportedCapability] = Field(
        default_factory=list,
        max_length=_COCKPIT_LIST_MAX_ITEMS,
        description="Explicit unsupported capabilities that must not be claimed by the cockpit.",
    )
    correlation_id: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Correlation id propagated from request or source evidence.",
        examples=["corr-rfc26-canonical"],
    )

    @field_validator(
        "action_item_id",
        "owning_system",
    )
    @classmethod
    def _action_required_refs_must_be_bounded(cls, value: str) -> str:
        return _normalize_required_identifier(value, field_name="cockpit action reference")

    @field_validator(
        "client_ref",
        "household_ref",
        "portfolio_id",
        "proposal_id",
        "workspace_id",
        "memo_id",
        "policy_evaluation_id",
        "report_ref",
        "execution_ref",
        "due_at",
        "source_timestamp",
        "correlation_id",
    )
    @classmethod
    def _action_optional_refs_must_be_bounded(cls, value: str | None) -> str | None:
        return _normalize_optional_identifier(value, field_name="cockpit action reference")

    @field_validator("title", "next_required_action")
    @classmethod
    def _action_copy_must_be_business_safe(cls, value: str) -> str:
        return _normalize_business_text(value, field_name="cockpit action copy")

    @field_validator("owner_role_label")
    @classmethod
    def _owner_role_label_must_be_business_safe(cls, value: str) -> str:
        return _normalize_business_text(value, field_name="cockpit owner role label")

    @field_validator("reason_codes")
    @classmethod
    def _reason_codes_must_be_bounded(cls, value: list[str]) -> list[str]:
        return _normalize_identifier_list(value, field_name="cockpit reason code")

    @model_validator(mode="after")
    def _owner_role_label_defaults_to_business_label(self) -> AdvisoryActionItem:
        if not self.owner_role_label:
            self.owner_role_label = cockpit_owner_role_label(self.owner_role)
        return self


class AdvisoryActionItemPage(BaseModel):
    items: list[AdvisoryActionItem] = Field(
        max_length=_COCKPIT_LIST_MAX_ITEMS,
        description="Action items visible to the caller.",
    )
    next_cursor: str | None = Field(
        default=None,
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Opaque cursor for retrieving the next action-item page.",
        examples=["eyJwcmlvcml0eSI6IkhJR0gifQ"],
    )
    page_size: int = Field(description="Effective bounded page size.", examples=[25])
    total_count: int | None = Field(
        default=None,
        description="Optional count when computed without unsafe full-book scans.",
        examples=[42],
    )

    @field_validator("next_cursor")
    @classmethod
    def _next_cursor_must_be_bounded(cls, value: str | None) -> str | None:
        return _normalize_optional_identifier(value, field_name="cockpit action page cursor")


class MeetingPreparationPacket(BaseModel):
    packet_id: str = Field(
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Stable meeting-preparation packet identifier.",
        examples=["prep_pb_sg_global_bal_001"],
    )
    context_type: Literal["PORTFOLIO", "PROPOSAL", "CLIENT", "HOUSEHOLD"] = Field(
        description="Source-backed preparation context.",
        examples=["PORTFOLIO"],
    )
    context_ref: str = Field(
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Portfolio, proposal, client, or household reference.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    status: AdvisorCockpitActionStatus = Field(
        description="Preparation readiness posture.",
        examples=["READY"],
    )
    evidence_refs: list[CockpitEvidenceRef] = Field(
        default_factory=list,
        max_length=_COCKPIT_LIST_MAX_ITEMS,
        description="Evidence references used to prepare advisor-facing material.",
    )
    sections: list[dict[str, Any]] = Field(
        default_factory=list,
        max_length=_COCKPIT_PREPARATION_SECTIONS_MAX_ITEMS,
        description=(
            "Source-backed preparation sections; raw restricted evidence must be projected."
        ),
    )

    @field_validator("packet_id", "context_ref")
    @classmethod
    def _packet_refs_must_be_bounded(cls, value: str) -> str:
        return _normalize_required_identifier(value, field_name="meeting preparation reference")


class AdvisorCockpitOperatingSnapshot(BaseModel):
    snapshot_id: str = Field(
        max_length=_COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Stable cockpit snapshot identifier.",
        examples=["cockpit_snapshot_sg_001"],
    )
    caller_context: CockpitCallerContext = Field(
        description="Caller context after server-side entitlement projection."
    )
    as_of: str = Field(
        description="UTC ISO8601 snapshot timestamp.",
        examples=["2026-05-27T08:00:00+00:00"],
    )
    action_counts: dict[str, int] = Field(
        default_factory=dict,
        max_length=_COCKPIT_SUPPORTABILITY_KEYS_MAX_ITEMS,
        description="Action counts by family, status, priority, owner role, or SLA band.",
        examples=[{"status.PENDING_REVIEW": 3, "priority.HIGH": 2}],
    )
    top_priority_actions: list[AdvisoryActionItem] = Field(
        default_factory=list,
        max_length=_COCKPIT_LIST_MAX_ITEMS,
        description="Bounded top-priority actions for cockpit summary display.",
    )
    preparation_packets: list[MeetingPreparationPacket] = Field(
        default_factory=list,
        max_length=_COCKPIT_LIST_MAX_ITEMS,
        description="Source-backed meeting-preparation packets visible to the caller.",
    )
    dependency_readiness: list[CockpitDependencyReadiness] = Field(
        default_factory=list,
        max_length=_COCKPIT_LIST_MAX_ITEMS,
        description="Snapshot-level dependency readiness posture.",
    )
    source_readiness_gaps: list[CockpitSourceReadinessGap] = Field(
        default_factory=list,
        max_length=_COCKPIT_LIST_MAX_ITEMS,
        description="Snapshot-level source readiness gaps.",
    )
    unsupported_capabilities: list[AdvisorCockpitUnsupportedCapability] = Field(
        default_factory=list,
        max_length=_COCKPIT_LIST_MAX_ITEMS,
        description="Unsupported capabilities that remain explicitly unclaimable.",
    )
    lineage_refs: list[CockpitLineageRef] = Field(
        default_factory=list,
        max_length=_COCKPIT_LIST_MAX_ITEMS,
        description="Snapshot lineage references for audit and replay.",
    )
    supportability: dict[str, Any] = Field(
        default_factory=dict,
        max_length=_COCKPIT_SUPPORTABILITY_KEYS_MAX_ITEMS,
        description="Support-safe operational posture for cockpit dependencies and freshness.",
    )

    @field_validator("snapshot_id", "as_of")
    @classmethod
    def _snapshot_refs_must_be_bounded(cls, value: str) -> str:
        return _normalize_required_identifier(value, field_name="cockpit snapshot reference")

    @field_validator("action_counts")
    @classmethod
    def _action_count_keys_must_be_bounded(cls, value: dict[str, int]) -> dict[str, int]:
        normalized: dict[str, int] = {}
        for key, count in value.items():
            normalized_key = _normalize_required_identifier(
                str(key),
                field_name="cockpit action count key",
            )
            if count < 0:
                raise ValueError("cockpit action counts cannot be negative")
            normalized[normalized_key] = count
        return normalized


def _normalize_required_identifier(value: str, *, field_name: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > _COCKPIT_IDENTIFIER_MAX_LENGTH:
        raise ValueError(f"{field_name} is too long")
    if _contains_sensitive_term(normalized):
        raise ValueError(f"{field_name} cannot contain sensitive technical detail")
    return normalized


def _normalize_optional_identifier(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    return _normalize_required_identifier(normalized, field_name=field_name)


def _normalize_business_text(value: str, *, field_name: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > _COCKPIT_TEXT_MAX_LENGTH:
        raise ValueError(f"{field_name} is too long")
    if _contains_sensitive_term(normalized):
        raise ValueError(f"{field_name} cannot contain sensitive technical detail")
    return normalized


def _normalize_optional_business_text(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    return _normalize_business_text(normalized, field_name=field_name)


def _normalize_identifier_list(value: list[str], *, field_name: str) -> list[str]:
    return [_normalize_required_identifier(str(item), field_name=field_name) for item in value]


def _contains_sensitive_term(value: str) -> bool:
    lowered = value.lower().replace("-", " ")
    return any(term in lowered for term in _COCKPIT_SENSITIVE_TERMS)
