"""Advisory simulation package."""

from src.core.advisory.alternatives_models import (
    AlternativeCandidateSeed,
    AlternativeComparisonSummary,
    AlternativeConstraintResult,
    AlternativeTradeoff,
    ProposalAlternative,
    ProposalAlternativesConstraints,
    ProposalAlternativesRequest,
    RejectedAlternativeCandidate,
)
from src.core.advisory.alternatives_normalizer import (
    AlternativesRequestNormalizationError,
    NormalizedProposalAlternativesRequest,
    normalize_alternatives_request,
)
from src.core.advisory.alternatives_strategies import (
    AlternativeConstructionStrategy,
    AlternativeStrategyInputs,
    build_candidate_seeds,
    build_initial_strategy_registry,
)

__all__ = [
    "AlternativeCandidateSeed",
    "AlternativeComparisonSummary",
    "AlternativeConstraintResult",
    "AlternativeConstructionStrategy",
    "AlternativeStrategyInputs",
    "AlternativeTradeoff",
    "AlternativesRequestNormalizationError",
    "NormalizedProposalAlternativesRequest",
    "ProposalAlternative",
    "ProposalAlternativesConstraints",
    "ProposalAlternativesRequest",
    "RejectedAlternativeCandidate",
    "build_candidate_seeds",
    "build_initial_strategy_registry",
    "normalize_alternatives_request",
]
