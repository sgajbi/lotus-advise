from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from src.core.advisor_cockpit import model_validation as cockpit_validation
from src.core.advisor_cockpit.action_models import AdvisoryActionItem
from src.core.advisor_cockpit.reference_models import (
    CockpitCallerContext,
    CockpitDependencyReadiness,
    CockpitEvidenceRef,
    CockpitLineageRef,
    CockpitSourceReadinessGap,
)
from src.core.advisor_cockpit.type_models import (
    AdvisorCockpitActionStatus,
    AdvisorCockpitUnsupportedCapability,
)

_COCKPIT_IDENTIFIER_MAX_LENGTH = cockpit_validation.COCKPIT_IDENTIFIER_MAX_LENGTH
_COCKPIT_LIST_MAX_ITEMS = cockpit_validation.COCKPIT_LIST_MAX_ITEMS
_COCKPIT_PREPARATION_SECTIONS_MAX_ITEMS = cockpit_validation.COCKPIT_PREPARATION_SECTIONS_MAX_ITEMS
_COCKPIT_SUPPORTABILITY_KEYS_MAX_ITEMS = cockpit_validation.COCKPIT_SUPPORTABILITY_KEYS_MAX_ITEMS
_normalize_required_identifier = cockpit_validation.normalize_required_identifier


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
