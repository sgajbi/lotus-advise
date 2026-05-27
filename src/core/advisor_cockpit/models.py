from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

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


class CockpitCallerContext(BaseModel):
    advisor_id: str | None = Field(
        default=None,
        description="Advisor identifier for advisor-scoped cockpit reads.",
        examples=["advisor_sg_001"],
    )
    desk_id: str | None = Field(
        default=None,
        description="Desk identifier for desk-head or supervisory cockpit reads.",
        examples=["sg_private_bank_desk"],
    )
    coverage_team_id: str | None = Field(
        default=None,
        description="Coverage-team identifier when a source-backed assignment exists.",
        examples=["coverage_team_sg_01"],
    )
    role: AdvisorCockpitOwnerRole = Field(
        description="Caller role used for server-side entitlement projection.",
        examples=["ADVISOR"],
    )
    demo_context: bool = Field(
        default=False,
        description="Whether the caller is using governed synthetic demo data.",
        examples=[True],
    )


class CockpitEvidenceRef(BaseModel):
    evidence_id: str = Field(
        description="Stable evidence identifier emitted by the source authority.",
        examples=["policy_eval_sg_001"],
    )
    evidence_type: str = Field(
        description="Evidence family, such as policy evaluation, memo, report, or supportability.",
        examples=["POLICY_EVALUATION"],
    )
    source_system: str = Field(
        description="Authoritative Lotus system that owns the evidence.",
        examples=["lotus-advise"],
    )
    access_class: CockpitEvidenceAccessClass = Field(
        description="Access class for projection and documentation controls.",
        examples=["RESTRICTED_CUSTOMER_EVIDENCE"],
    )
    summary: str = Field(
        description="Support-safe evidence summary for advisor cockpit display.",
        examples=["Policy evaluation requires compliance review."],
    )


class CockpitLineageRef(BaseModel):
    lineage_id: str = Field(
        description="Stable lineage reference for audit and replay.",
        examples=["lineage_policy_eval_sg_001"],
    )
    source_system: str = Field(
        description="System that produced the lineage reference.",
        examples=["lotus-advise"],
    )
    content_hash: str | None = Field(
        default=None,
        description="Optional canonical hash for immutable source evidence.",
        examples=["sha256:policy-evaluation"],
    )


class CockpitSourceReadinessGap(BaseModel):
    source_family: str = Field(
        description="Source family with missing, stale, degraded, or unsupported evidence.",
        examples=["policy"],
    )
    gap_code: str = Field(
        description="Machine-readable source readiness gap code.",
        examples=["POLICY_REVIEW_PENDING"],
    )
    owner_role: AdvisorCockpitOwnerRole = Field(
        description="Role expected to resolve or own the gap.",
        examples=["COMPLIANCE_REVIEWER"],
    )
    message: str = Field(
        description="Business-facing support-safe explanation of the source gap.",
        examples=["Policy review is pending before client-ready posture can change."],
    )


class CockpitDependencyReadiness(BaseModel):
    dependency: str = Field(
        description="Dependency or source family name.",
        examples=["lotus-report"],
    )
    state: CockpitDependencyState = Field(
        description="Dependency readiness posture.",
        examples=["DEGRADED"],
    )
    reason_code: str = Field(
        description="Bounded machine-readable readiness reason.",
        examples=["REPORT_PACKAGE_UNAVAILABLE"],
    )
    summary: str = Field(
        description="Support-safe dependency readiness summary.",
        examples=["Report package status is degraded; advisor action remains blocked."],
    )


class CockpitAcknowledgementState(BaseModel):
    acknowledged: bool = Field(
        description="Whether an advisory-owned action has been acknowledged.",
        examples=[False],
    )
    acknowledgement_id: str | None = Field(
        default=None,
        description="Append-only acknowledgement identifier when present.",
        examples=["ack_001"],
    )
    acknowledged_by: str | None = Field(
        default=None,
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
        description="Support-safe acknowledgement note.",
        examples=["Advisor has reviewed the pending compliance action."],
    )


class AdvisoryActionItem(BaseModel):
    action_item_id: str = Field(
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
        description="Role that owns the next step or external handoff.",
        examples=["COMPLIANCE_REVIEWER"],
    )
    owning_system: str = Field(
        description="System of record for the current action state.",
        examples=["lotus-advise"],
    )
    title: str = Field(
        description="Business-facing action title.",
        examples=["Policy review required"],
    )
    next_required_action: str = Field(
        description="Backend-owned next action; Workbench must render, not infer.",
        examples=["Review policy evaluation before advisor follow-up."],
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Deterministic reason codes explaining status and priority.",
        examples=[["POLICY_PENDING_REVIEW", "CLIENT_READY_BLOCKED"]],
    )
    client_ref: str | None = Field(default=None, description="Source-backed client reference.")
    household_ref: str | None = Field(
        default=None, description="Source-backed household reference when available."
    )
    portfolio_id: str | None = Field(
        default=None,
        description="Source-backed portfolio identifier.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    proposal_id: str | None = Field(default=None, description="Source-backed proposal identifier.")
    workspace_id: str | None = Field(default=None, description="Source-backed workspace id.")
    memo_id: str | None = Field(default=None, description="Source-backed memo id.")
    policy_evaluation_id: str | None = Field(
        default=None,
        description="Source-backed policy evaluation id.",
        examples=["policy_eval_sg_001"],
    )
    report_ref: str | None = Field(default=None, description="Source-backed report reference.")
    execution_ref: str | None = Field(
        default=None, description="Source-backed execution handoff/status reference."
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
        description="UTC ISO8601 timestamp for the source event or evidence that created action.",
        examples=["2026-05-27T07:30:00+00:00"],
    )
    evidence_refs: list[CockpitEvidenceRef] = Field(
        default_factory=list,
        description="Source-owned evidence references that justify the action.",
    )
    source_readiness_gaps: list[CockpitSourceReadinessGap] = Field(
        default_factory=list,
        description="Missing, stale, degraded, or unsupported source evidence gaps.",
    )
    dependency_readiness: list[CockpitDependencyReadiness] = Field(
        default_factory=list,
        description="Dependency readiness posture relevant to the action.",
    )
    lineage_refs: list[CockpitLineageRef] = Field(
        default_factory=list,
        description="Lineage references for audit and replay.",
    )
    acknowledgement_state: CockpitAcknowledgementState = Field(
        default_factory=lambda: CockpitAcknowledgementState(acknowledged=False),
        description="Advisory-owned acknowledgement posture.",
    )
    unsupported_capabilities: list[AdvisorCockpitUnsupportedCapability] = Field(
        default_factory=list,
        description="Explicit unsupported capabilities that must not be claimed by the cockpit.",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Correlation id propagated from request or source evidence.",
        examples=["corr-rfc26-canonical"],
    )


class AdvisoryActionItemPage(BaseModel):
    items: list[AdvisoryActionItem] = Field(description="Action items visible to the caller.")
    next_cursor: str | None = Field(
        default=None,
        description="Opaque cursor for retrieving the next action-item page.",
        examples=["eyJwcmlvcml0eSI6IkhJR0gifQ"],
    )
    page_size: int = Field(description="Effective bounded page size.", examples=[25])
    total_count: int | None = Field(
        default=None,
        description="Optional count when computed without unsafe full-book scans.",
        examples=[42],
    )


class MeetingPreparationPacket(BaseModel):
    packet_id: str = Field(
        description="Stable meeting-preparation packet identifier.",
        examples=["prep_pb_sg_global_bal_001"],
    )
    context_type: Literal["PORTFOLIO", "PROPOSAL", "CLIENT", "HOUSEHOLD"] = Field(
        description="Source-backed preparation context.",
        examples=["PORTFOLIO"],
    )
    context_ref: str = Field(
        description="Portfolio, proposal, client, or household reference.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    status: AdvisorCockpitActionStatus = Field(
        description="Preparation readiness posture.",
        examples=["READY"],
    )
    evidence_refs: list[CockpitEvidenceRef] = Field(
        default_factory=list,
        description="Evidence references used to prepare advisor-facing material.",
    )
    sections: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Source-backed preparation sections; raw restricted evidence must be projected."
        ),
    )


class AdvisorCockpitOperatingSnapshot(BaseModel):
    snapshot_id: str = Field(
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
        description="Action counts by family, status, priority, owner role, or SLA band.",
        examples=[{"status.PENDING_REVIEW": 3, "priority.HIGH": 2}],
    )
    top_priority_actions: list[AdvisoryActionItem] = Field(
        default_factory=list,
        description="Bounded top-priority actions for cockpit summary display.",
    )
    preparation_packets: list[MeetingPreparationPacket] = Field(
        default_factory=list,
        description="Source-backed meeting-preparation packets visible to the caller.",
    )
    dependency_readiness: list[CockpitDependencyReadiness] = Field(
        default_factory=list,
        description="Snapshot-level dependency readiness posture.",
    )
    source_readiness_gaps: list[CockpitSourceReadinessGap] = Field(
        default_factory=list,
        description="Snapshot-level source readiness gaps.",
    )
    unsupported_capabilities: list[AdvisorCockpitUnsupportedCapability] = Field(
        default_factory=list,
        description="Unsupported capabilities that remain explicitly unclaimable.",
    )
    lineage_refs: list[CockpitLineageRef] = Field(
        default_factory=list,
        description="Snapshot lineage references for audit and replay.",
    )
    supportability: dict[str, Any] = Field(
        default_factory=dict,
        description="Support-safe operational posture for cockpit dependencies and freshness.",
    )
