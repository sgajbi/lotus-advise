from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from src.core.advisory.proposal_review_evidence_models import (
    BenchmarkAssignmentReasonCode,
)

BenchmarkAssignmentEvidenceSupportability = Literal["READY", "PARTIAL"]


@dataclass(frozen=True)
class BenchmarkAssignmentSourceEvidence:
    """Source-owned assignment facts after the integration anti-corruption boundary."""

    effective_benchmark_id: str
    effective_as_of_date: str
    effective_from_date: str
    effective_to_date: str | None
    assignment_source: str
    assignment_status: str
    assignment_recorded_at: datetime
    assignment_version: int
    assignment_policy_pack_id: str | None
    assignment_source_system: str | None
    assignment_contract_version: str
    source_product_name: str
    source_product_version: str
    source_tenant_id: str | None
    source_generated_at: datetime
    source_restatement_version: str
    source_reconciliation_status: str
    source_data_quality_status: str
    source_latest_evidence_at: datetime | None
    source_batch_fingerprint: str | None
    source_snapshot_id: str | None
    source_content_hash: str
    source_references: tuple[str, ...]
    source_lineage: dict[str, str]
    source_evidence_current: bool
    source_freshness_status: str
    source_policy_version: str | None
    supportability: BenchmarkAssignmentEvidenceSupportability
    reason_code: BenchmarkAssignmentReasonCode | None = None


@dataclass(frozen=True)
class BenchmarkAssignmentEvidenceResolution:
    """A fail-closed source resolution for the current proposal state."""

    source_evidence: BenchmarkAssignmentSourceEvidence | None
    reason_code: BenchmarkAssignmentReasonCode | None = None

    @classmethod
    def unavailable(
        cls, reason_code: BenchmarkAssignmentReasonCode
    ) -> "BenchmarkAssignmentEvidenceResolution":
        return cls(source_evidence=None, reason_code=reason_code)


__all__ = [
    "BenchmarkAssignmentEvidenceResolution",
    "BenchmarkAssignmentEvidenceSupportability",
    "BenchmarkAssignmentSourceEvidence",
]
