from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.advisor_cockpit import model_validation as cockpit_validation
from src.core.advisor_cockpit.type_models import (
    AdvisorCockpitCallerRole,
    AdvisorCockpitOwnerRole,
    CockpitDependencyState,
    CockpitEvidenceAccessClass,
)

_COCKPIT_IDENTIFIER_MAX_LENGTH = cockpit_validation.COCKPIT_IDENTIFIER_MAX_LENGTH
_COCKPIT_SUMMARY_MAX_LENGTH = cockpit_validation.COCKPIT_SUMMARY_MAX_LENGTH
_normalize_required_identifier = cockpit_validation.normalize_required_identifier
_normalize_optional_identifier = cockpit_validation.normalize_optional_identifier
_normalize_business_text = cockpit_validation.normalize_business_text
_normalize_optional_business_text = cockpit_validation.normalize_optional_business_text


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
