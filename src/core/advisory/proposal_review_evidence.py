from __future__ import annotations

from collections.abc import Mapping

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
    benchmark_assignment_evidence: BenchmarkAssignmentEvidence | None = None,
) -> ProposalReviewEvidence:
    """Project source-owned review evidence without deriving advisory facts locally."""

    mandate_id = _optional_text(policy_context, "mandate_id")
    return ProposalReviewEvidence(
        benchmark_assignment=_build_benchmark_assignment_evidence(
            requested_benchmark_id=_optional_text(policy_context, "benchmark_id"),
            requested_as_of_date=valuation_context.current_state.requested_as_of_date,
            source_evidence=benchmark_assignment_evidence,
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
    source_evidence: BenchmarkAssignmentEvidence | None,
) -> BenchmarkAssignmentEvidence:
    if source_evidence is None:
        return BenchmarkAssignmentEvidence(
            requested_benchmark_id=requested_benchmark_id,
            requested_as_of_date=requested_as_of_date,
            supportability="UNAVAILABLE",
            reason_code="BENCHMARK_EVIDENCE_UNAVAILABLE",
        )
    effective_id = source_evidence.effective_benchmark_id
    requested_matches = requested_benchmark_id in (None, effective_id)
    assignment_mismatch = effective_id is not None and not requested_matches
    updates: dict[str, object] = {
        "requested_benchmark_id": requested_benchmark_id,
        "requested_as_of_date": requested_as_of_date,
    }
    if assignment_mismatch:
        updates["supportability"] = "RESTRICTED"
        updates["reason_code"] = "BENCHMARK_EVIDENCE_ASSIGNMENT_MISMATCH"
    updated: BenchmarkAssignmentEvidence = source_evidence.model_copy(update=updates)
    return updated


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
