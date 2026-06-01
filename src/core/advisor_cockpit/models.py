from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.advisor_cockpit import model_validation as cockpit_validation
from src.core.advisor_cockpit.reference_models import (
    CockpitAcknowledgementState as CockpitAcknowledgementState,
)
from src.core.advisor_cockpit.reference_models import (
    CockpitCallerContext as CockpitCallerContext,
)
from src.core.advisor_cockpit.reference_models import (
    CockpitDependencyReadiness as CockpitDependencyReadiness,
)
from src.core.advisor_cockpit.reference_models import (
    CockpitEvidenceRef as CockpitEvidenceRef,
)
from src.core.advisor_cockpit.reference_models import (
    CockpitLineageRef as CockpitLineageRef,
)
from src.core.advisor_cockpit.reference_models import (
    CockpitSourceReadinessGap as CockpitSourceReadinessGap,
)
from src.core.advisor_cockpit.type_models import (
    AdvisorCockpitActionFamily as AdvisorCockpitActionFamily,
)
from src.core.advisor_cockpit.type_models import (
    AdvisorCockpitActionPriority as AdvisorCockpitActionPriority,
)
from src.core.advisor_cockpit.type_models import (
    AdvisorCockpitActionStatus as AdvisorCockpitActionStatus,
)
from src.core.advisor_cockpit.type_models import (
    AdvisorCockpitCallerRole as AdvisorCockpitCallerRole,
)
from src.core.advisor_cockpit.type_models import (
    AdvisorCockpitOwnerRole as AdvisorCockpitOwnerRole,
)
from src.core.advisor_cockpit.type_models import (
    AdvisorCockpitSlaAgeBand as AdvisorCockpitSlaAgeBand,
)
from src.core.advisor_cockpit.type_models import (
    AdvisorCockpitUnsupportedCapability as AdvisorCockpitUnsupportedCapability,
)
from src.core.advisor_cockpit.type_models import (
    CockpitDependencyState as CockpitDependencyState,
)
from src.core.advisor_cockpit.type_models import (
    CockpitEvidenceAccessClass as CockpitEvidenceAccessClass,
)

_COCKPIT_IDENTIFIER_MAX_LENGTH = cockpit_validation.COCKPIT_IDENTIFIER_MAX_LENGTH
_COCKPIT_TEXT_MAX_LENGTH = cockpit_validation.COCKPIT_TEXT_MAX_LENGTH
_COCKPIT_SUMMARY_MAX_LENGTH = cockpit_validation.COCKPIT_SUMMARY_MAX_LENGTH
_COCKPIT_LIST_MAX_ITEMS = cockpit_validation.COCKPIT_LIST_MAX_ITEMS
_COCKPIT_PREPARATION_SECTIONS_MAX_ITEMS = cockpit_validation.COCKPIT_PREPARATION_SECTIONS_MAX_ITEMS
_COCKPIT_SUPPORTABILITY_KEYS_MAX_ITEMS = cockpit_validation.COCKPIT_SUPPORTABILITY_KEYS_MAX_ITEMS
cockpit_owner_role_label = cockpit_validation.cockpit_owner_role_label
_normalize_required_identifier = cockpit_validation.normalize_required_identifier
_normalize_optional_identifier = cockpit_validation.normalize_optional_identifier
_normalize_business_text = cockpit_validation.normalize_business_text
_normalize_optional_business_text = cockpit_validation.normalize_optional_business_text
_normalize_identifier_list = cockpit_validation.normalize_identifier_list


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
