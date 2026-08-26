from __future__ import annotations

from collections.abc import Mapping

from src.core.advisory.benchmark_assignment_evidence import (
    BenchmarkAssignmentEvidenceResolution,
)
from src.core.advisory.proposal_review_evidence_models import (
    BenchmarkAssignmentEvidence,
    MandateLimitEvidenceState,
    ProposalReviewEvidence,
)
from src.core.advisory.valuation_context_models import ProposalValuationContext


def build_proposal_review_evidence(
    *,
    policy_context: Mapping[str, object] | None,
    valuation_context: ProposalValuationContext,
    benchmark_assignment_resolution: BenchmarkAssignmentEvidenceResolution | None = None,
) -> ProposalReviewEvidence:
    """Project source-owned review evidence without deriving advisory facts locally."""

    mandate_id = _optional_text(policy_context, "mandate_id")
    return ProposalReviewEvidence(
        benchmark_assignment=_build_benchmark_assignment_evidence(
            requested_benchmark_id=_optional_text(policy_context, "benchmark_id"),
            requested_as_of_date=valuation_context.current_state.requested_as_of_date,
            resolution=benchmark_assignment_resolution,
        ),
        current_mandate_limits=_build_mandate_limit_state(
            mandate_id=mandate_id,
            requested_as_of_date=valuation_context.current_state.requested_as_of_date,
        ),
        simulated_mandate_limits=_build_mandate_limit_state(
            mandate_id=mandate_id,
            requested_as_of_date=valuation_context.simulated_state.requested_as_of_date,
        ),
    )


def _build_benchmark_assignment_evidence(
    *,
    requested_benchmark_id: str | None,
    requested_as_of_date: str | None,
    resolution: BenchmarkAssignmentEvidenceResolution | None,
) -> BenchmarkAssignmentEvidence:
    source_evidence = resolution.source_evidence if resolution is not None else None
    if source_evidence is None:
        return BenchmarkAssignmentEvidence(
            requested_benchmark_id=requested_benchmark_id,
            requested_as_of_date=requested_as_of_date,
            supportability="UNAVAILABLE",
            reason_code=(
                resolution.reason_code
                if resolution is not None and resolution.reason_code is not None
                else "BENCHMARK_EVIDENCE_UNAVAILABLE"
            ),
        )
    return BenchmarkAssignmentEvidence(
        requested_benchmark_id=requested_benchmark_id,
        effective_benchmark_id=source_evidence.effective_benchmark_id,
        requested_as_of_date=requested_as_of_date,
        effective_as_of_date=source_evidence.effective_as_of_date,
        effective_from_date=source_evidence.effective_from_date,
        effective_to_date=source_evidence.effective_to_date,
        assignment_source=source_evidence.assignment_source,
        assignment_status=source_evidence.assignment_status,
        assignment_recorded_at=source_evidence.assignment_recorded_at,
        assignment_version=source_evidence.assignment_version,
        assignment_policy_pack_id=source_evidence.assignment_policy_pack_id,
        assignment_source_system=source_evidence.assignment_source_system,
        assignment_contract_version=source_evidence.assignment_contract_version,
        source_service="LOTUS_CORE",
        source_product_name=source_evidence.source_product_name,
        source_product_version=source_evidence.source_product_version,
        source_tenant_id=source_evidence.source_tenant_id,
        source_generated_at=source_evidence.source_generated_at,
        source_restatement_version=source_evidence.source_restatement_version,
        source_reconciliation_status=source_evidence.source_reconciliation_status,
        source_data_quality_status=source_evidence.source_data_quality_status,
        source_latest_evidence_at=source_evidence.source_latest_evidence_at,
        source_batch_fingerprint=source_evidence.source_batch_fingerprint,
        source_snapshot_id=source_evidence.source_snapshot_id,
        benchmark_assignment_content_hash=source_evidence.source_content_hash,
        source_references=list(source_evidence.source_references),
        source_lineage=source_evidence.source_lineage,
        source_evidence_current=source_evidence.source_evidence_current,
        source_freshness_status=source_evidence.source_freshness_status,
        source_policy_version=source_evidence.source_policy_version,
        supportability=source_evidence.supportability,
        reason_code=source_evidence.reason_code,
    )


def _build_mandate_limit_state(
    mandate_id: str | None, requested_as_of_date: str | None
) -> MandateLimitEvidenceState:
    return MandateLimitEvidenceState(
        mandate_id=mandate_id,
        requested_as_of_date=requested_as_of_date,
        supportability="UNAVAILABLE",
        reason_code="MANDATE_LIMIT_EVIDENCE_UNAVAILABLE",
    )


def _optional_text(context: Mapping[str, object] | None, key: str) -> str | None:
    value = context.get(key) if context is not None else None
    return value.strip() if isinstance(value, str) and value.strip() else None
