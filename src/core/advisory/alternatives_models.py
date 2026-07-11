"""Compatibility exports for proposal-alternatives model contracts."""

from src.core.advisory.alternatives_request_models import (
    AlternativeMoneyConstraint,
    ProposalAlternativesConstraints,
    ProposalAlternativesRequest,
)
from src.core.advisory.alternatives_response_models import (
    AlternativeAllocationDelta,
    AlternativeApprovalDelta,
    AlternativeCandidateSeed,
    AlternativeCashDelta,
    AlternativeComparatorInputs,
    AlternativeComparisonSummary,
    AlternativeConstraintResult,
    AlternativeCostDelta,
    AlternativeCurrencyDelta,
    AlternativeRankingProjection,
    AlternativeRiskDelta,
    AlternativeTradeoff,
    ProposalAlternative,
    ProposalAlternatives,
    RejectedAlternativeCandidate,
)
from src.core.advisory.alternatives_types import (
    AlternativeCandidateStatus,
    AlternativeConstructionObjective,
    AlternativeEvidenceRequirement,
    AlternativeStatus,
)

__all__ = [
    "AlternativeAllocationDelta",
    "AlternativeApprovalDelta",
    "AlternativeCandidateSeed",
    "AlternativeCandidateStatus",
    "AlternativeCashDelta",
    "AlternativeComparisonSummary",
    "AlternativeComparatorInputs",
    "AlternativeConstructionObjective",
    "AlternativeConstraintResult",
    "AlternativeCostDelta",
    "AlternativeCurrencyDelta",
    "AlternativeEvidenceRequirement",
    "AlternativeMoneyConstraint",
    "AlternativeRankingProjection",
    "AlternativeRiskDelta",
    "AlternativeStatus",
    "AlternativeTradeoff",
    "ProposalAlternative",
    "ProposalAlternatives",
    "ProposalAlternativesConstraints",
    "ProposalAlternativesRequest",
    "RejectedAlternativeCandidate",
]
