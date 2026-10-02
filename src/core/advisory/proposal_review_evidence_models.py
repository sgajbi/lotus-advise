from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ProposalReviewEvidenceSupportability = Literal[
    "READY", "PARTIAL", "RESTRICTED", "UNAVAILABLE", "NOT_SUPPORTED"
]
BenchmarkAssignmentReasonCode = Literal[
    "BENCHMARK_EVIDENCE_UNAVAILABLE",
    "BENCHMARK_EVIDENCE_REQUESTED_AS_OF_MISSING",
    "BENCHMARK_EVIDENCE_SOURCE_UNAVAILABLE",
    "BENCHMARK_EVIDENCE_SOURCE_NOT_FOUND",
    "BENCHMARK_EVIDENCE_SOURCE_INVALID",
    "BENCHMARK_EVIDENCE_SOURCE_DEGRADED",
    "BENCHMARK_EVIDENCE_PORTFOLIO_MISMATCH",
    "BENCHMARK_EVIDENCE_AS_OF_MISMATCH",
    "BENCHMARK_EVIDENCE_TENANT_REQUIRED",
    "BENCHMARK_EVIDENCE_TENANT_MISMATCH",
    "BENCHMARK_EVIDENCE_ASSIGNMENT_MISMATCH",
]
MandateLimitReasonCode = Literal["MANDATE_LIMIT_EVIDENCE_UNAVAILABLE"]
MandateLimitOutcome = Literal["WITHIN_LIMIT", "BREACH", "PENDING_REVIEW", "UNAVAILABLE"]
MandateLimitSeverity = Literal["INFO", "WARNING", "BLOCKING"]


def _field(description: str, example: object, **kwargs: Any) -> Any:
    return Field(description=description, examples=[example], **kwargs)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BenchmarkAssignmentEvidence(_StrictModel):
    requested_benchmark_id: str | None = _field("Requested ID.", "BM_1", default=None)
    effective_benchmark_id: str | None = _field("Applied ID.", "BM_1", default=None)
    requested_as_of_date: str | None = _field("Requested date.", "2026-03-25", default=None)
    effective_as_of_date: str | None = _field("Applied date.", "2026-03-25", default=None)
    effective_from_date: str | None = _field(
        "Assignment effective start.", "2026-01-01", default=None
    )
    effective_to_date: str | None = _field("Assignment effective end.", "2026-12-31", default=None)
    assignment_source: str | None = _field("Assignment source.", "policy_engine", default=None)
    assignment_status: str | None = _field("Assignment status.", "active", default=None)
    assignment_recorded_at: datetime | None = _field(
        "Assignment record time.", "2026-03-25T09:15:00Z", default=None
    )
    assignment_version: int | None = _field("Assignment version.", 3, default=None, ge=1)
    assignment_policy_pack_id: str | None = _field("Source policy pack.", "policy-v1", default=None)
    assignment_source_system: str | None = _field("Source system.", "mandate-book", default=None)
    assignment_contract_version: str | None = _field("Source contract.", "rfc_062_v1", default=None)
    source_service: str | None = _field("Evidence source.", "LOTUS_CORE", default=None)
    source_product_name: str | None = _field("Source product.", "BenchmarkAssignment", default=None)
    source_product_version: str | None = _field("Source product version.", "v1", default=None)
    source_tenant_id: str | None = _field("Source tenant scope.", "tenant-sg", default=None)
    source_generated_at: datetime | None = _field(
        "Source generation time.", "2026-03-25T09:16:00Z", default=None
    )
    source_restatement_version: str | None = _field("Restatement version.", "v1", default=None)
    source_reconciliation_status: str | None = _field(
        "Reconciliation status.", "RECONCILED", default=None
    )
    source_data_quality_status: str | None = _field(
        "Data-quality status.", "COMPLETE", default=None
    )
    source_latest_evidence_at: datetime | None = _field(
        "Latest source evidence time.", "2026-03-25T09:14:00Z", default=None
    )
    source_batch_fingerprint: str | None = _field("Source batch identity.", "batch-1", default=None)
    source_snapshot_id: str | None = _field("Source snapshot identity.", "snapshot-1", default=None)
    benchmark_assignment_content_hash: str | None = _field(
        "Deterministic source response hash.",
        "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    source_evidence_current: bool | None = _field("Source evidence current.", True, default=None)
    source_freshness_status: str | None = _field("Source freshness.", "CURRENT", default=None)
    source_policy_version: str | None = _field("Source policy version.", "policy-v1", default=None)
    source_references: list[str] = _field("Evidence references.", ["ref"], default_factory=list)
    source_lineage: dict[str, str] = _field(
        "Source lineage.", {"owner": "lotus-core"}, default_factory=dict
    )
    supportability: ProposalReviewEvidenceSupportability = _field("Supportability.", "UNAVAILABLE")
    reason_code: BenchmarkAssignmentReasonCode | None = _field(
        "Evidence reason.", "BENCHMARK_EVIDENCE_UNAVAILABLE", default=None
    )


class MandateLimitObservation(_StrictModel):
    limit_code: str = _field("Stable limit code.", "MAX_POSITION")
    limit_name: str = _field("Limit display name.", "Maximum position")
    dimension: str = _field("Measured dimension.", "instrument_weight")
    scope: str = _field("Limit scope.", "portfolio")
    observed_value: Decimal | None = _field("Observed value.", 0.08, default=None)
    minimum: Decimal | None = _field("Inclusive lower bound.", 0, default=None)
    maximum: Decimal | None = _field("Inclusive upper bound.", 0.1, default=None)
    unit: str | None = _field("Value unit.", "PERCENT_OF_NAV", default=None)
    currency: str | None = _field("Monetary currency.", "USD", default=None)
    outcome: MandateLimitOutcome = _field("Limit outcome.", "WITHIN_LIMIT")
    severity: MandateLimitSeverity | None = _field("Limit severity.", "INFO", default=None)
    source_references: list[str] = _field("Observation references.", ["ref"], default_factory=list)


class MandateLimitEvidenceState(_StrictModel):
    mandate_id: str | None = _field("Mandate ID.", "MANDATE_1", default=None)
    requested_as_of_date: str | None = _field("Requested date.", "2026-03-25", default=None)
    effective_as_of_date: str | None = _field("Applied date.", "2026-03-25", default=None)
    observations: list[MandateLimitObservation] = _field(
        "Limit observations.", [], default_factory=list
    )
    source_service: str | None = _field("Evidence source.", "LOTUS_CORE", default=None)
    supportability: ProposalReviewEvidenceSupportability = _field("Supportability.", "UNAVAILABLE")
    reason_code: MandateLimitReasonCode | None = _field(
        "Evidence reason.", "MANDATE_LIMIT_EVIDENCE_UNAVAILABLE", default=None
    )


class ProposalReviewEvidence(_StrictModel):
    schema_version: Literal["lotus.proposal-review-evidence.v1"] = _field(
        "Contract version.",
        "lotus.proposal-review-evidence.v1",
        default="lotus.proposal-review-evidence.v1",
    )
    benchmark_assignment: BenchmarkAssignmentEvidence = _field("Benchmark evidence.", {})
    current_mandate_limits: MandateLimitEvidenceState = _field("Current limit evidence.", {})
    simulated_mandate_limits: MandateLimitEvidenceState = _field("Simulated limit evidence.", {})

    @classmethod
    def unavailable(cls) -> "ProposalReviewEvidence":
        unavailable_mandate = {
            "supportability": "UNAVAILABLE",
            "reason_code": "MANDATE_LIMIT_EVIDENCE_UNAVAILABLE",
        }
        return cls(
            benchmark_assignment=BenchmarkAssignmentEvidence(
                supportability="UNAVAILABLE", reason_code="BENCHMARK_EVIDENCE_UNAVAILABLE"
            ),
            current_mandate_limits=unavailable_mandate,
            simulated_mandate_limits=unavailable_mandate,
        )
