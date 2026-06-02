from src.core.advisory.alternatives_models import (
    AlternativeCandidateSeed,
    AlternativeConstructionObjective,
    RejectedAlternativeCandidate,
)
from src.core.advisory.alternatives_normalizer import NormalizedProposalAlternativesRequest
from src.core.advisory.alternatives_strategy_base import AlternativeConstructionStrategy
from src.core.advisory.alternatives_strategy_models import (
    AlternativeStrategyBuildResult,
    AlternativeStrategyInputs,
    StrategyPosition,
    StrategyShelfInstrument,
    StrategyTradeIntent,
)
from src.core.advisory.alternatives_strategy_objectives import (
    AvoidRestrictedProductsStrategy,
    ImproveCurrencyAlignmentStrategy,
    LowerTurnoverStrategy,
    RaiseCashStrategy,
    ReduceConcentrationStrategy,
)
from src.core.advisory.alternatives_strategy_support import (
    candidate_id as _candidate_id,
)

__all__ = [
    "AlternativeConstructionStrategy",
    "AlternativeStrategyBuildResult",
    "AlternativeStrategyInputs",
    "AvoidRestrictedProductsStrategy",
    "ImproveCurrencyAlignmentStrategy",
    "LowerTurnoverStrategy",
    "RaiseCashStrategy",
    "ReduceConcentrationStrategy",
    "StrategyPosition",
    "StrategyShelfInstrument",
    "StrategyTradeIntent",
    "build_candidate_plan",
    "build_candidate_seeds",
    "build_initial_strategy_registry",
]


def build_initial_strategy_registry() -> dict[
    AlternativeConstructionObjective, AlternativeConstructionStrategy
]:
    strategies: tuple[AlternativeConstructionStrategy, ...] = (
        ReduceConcentrationStrategy(),
        RaiseCashStrategy(),
        LowerTurnoverStrategy(),
        ImproveCurrencyAlignmentStrategy(),
        AvoidRestrictedProductsStrategy(),
    )
    return {strategy.objective: strategy for strategy in strategies}


def build_candidate_plan(
    *,
    request: NormalizedProposalAlternativesRequest,
    inputs: AlternativeStrategyInputs,
    registry: dict[AlternativeConstructionObjective, AlternativeConstructionStrategy] | None = None,
) -> AlternativeStrategyBuildResult:
    strategies = registry or build_initial_strategy_registry()
    seeds: list[AlternativeCandidateSeed] = []
    rejected_candidates: list[RejectedAlternativeCandidate] = []
    for objective in request.requested_objectives:
        strategy = strategies.get(objective)
        if strategy is None:
            rejected_candidates.append(
                RejectedAlternativeCandidate(
                    candidate_id=_candidate_id(
                        objective=objective,
                        portfolio_id=inputs.portfolio_id,
                        pivot=inputs.base_currency,
                    ),
                    objective=objective,
                    status="REJECTED_CONSTRAINT_VIOLATION",
                    reason_code="ALTERNATIVE_OBJECTIVE_NOT_REGISTERED",
                    summary="Requested objective does not have a registered construction strategy.",
                    evidence_refs=[f"portfolio:{inputs.portfolio_id}"],
                )
            )
            continue
        result = strategy.build_result(request=request, inputs=inputs)
        seeds.extend(result.seeds)
        rejected_candidates.extend(result.rejected_candidates)
    return AlternativeStrategyBuildResult(
        seeds=tuple(seeds),
        rejected_candidates=tuple(rejected_candidates),
    )


def build_candidate_seeds(
    *,
    request: NormalizedProposalAlternativesRequest,
    inputs: AlternativeStrategyInputs,
    registry: dict[AlternativeConstructionObjective, AlternativeConstructionStrategy] | None = None,
) -> tuple[AlternativeCandidateSeed, ...]:
    return build_candidate_plan(request=request, inputs=inputs, registry=registry).seeds
