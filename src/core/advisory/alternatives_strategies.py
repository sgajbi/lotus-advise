from abc import ABC, abstractmethod
from typing import Iterable

from pydantic import BaseModel, Field

from src.core.advisory.alternatives_models import (
    AlternativeCandidateSeed,
    AlternativeConstructionObjective,
    AlternativeEvidenceRequirement,
)
from src.core.advisory.alternatives_normalizer import NormalizedProposalAlternativesRequest


class AlternativeStrategyInputs(BaseModel):
    portfolio_id: str = Field(
        description="Portfolio identifier associated with the baseline proposal."
    )
    base_currency: str = Field(description="Baseline portfolio currency.")
    held_instrument_ids: tuple[str, ...] = Field(
        default=(),
        description="Deterministic ordered held instrument ids from the baseline portfolio.",
    )
    shelf_instrument_ids: tuple[str, ...] = Field(
        default=(),
        description="Deterministic ordered shelf-backed instrument ids available to the strategy.",
    )
    current_trade_instrument_ids: tuple[str, ...] = Field(
        default=(),
        description=(
            "Deterministic ordered trade instrument ids from the baseline proposal request."
        ),
    )


class AlternativeConstructionStrategy(ABC):
    strategy_id: str
    objective: AlternativeConstructionObjective
    required_evidence: tuple[AlternativeEvidenceRequirement, ...] = ()

    @abstractmethod
    def build_seeds(
        self,
        *,
        request: NormalizedProposalAlternativesRequest,
        inputs: AlternativeStrategyInputs,
    ) -> tuple[AlternativeCandidateSeed, ...]:
        """Build deterministic candidate seeds without upstream service calls."""


class _SingleSeedStrategy(AlternativeConstructionStrategy):
    label: str
    summary: str

    def build_seeds(
        self,
        *,
        request: NormalizedProposalAlternativesRequest,
        inputs: AlternativeStrategyInputs,
    ) -> tuple[AlternativeCandidateSeed, ...]:
        pivot_instrument = _first_value(
            inputs.current_trade_instrument_ids
            or inputs.held_instrument_ids
            or inputs.shelf_instrument_ids
        )
        candidate_id = _candidate_id(
            objective=self.objective,
            portfolio_id=inputs.portfolio_id,
            pivot=pivot_instrument or inputs.base_currency,
        )
        return (
            AlternativeCandidateSeed(
                candidate_id=candidate_id,
                objective=self.objective,
                strategy_id=self.strategy_id,
                label=self.label,
                summary=self.summary,
                required_evidence=list(self.required_evidence),
                metadata={
                    "portfolio_id": inputs.portfolio_id,
                    "base_currency": inputs.base_currency,
                    "pivot_instrument_id": pivot_instrument,
                    "objective_rank": request.requested_objectives.index(self.objective),
                },
            ),
        )


class ReduceConcentrationStrategy(_SingleSeedStrategy):
    strategy_id = "reduce_concentration_v1"
    objective = "REDUCE_CONCENTRATION"
    label = "Reduce concentration"
    summary = "Generate a concentration-reduction candidate seeded from the baseline portfolio."


class RaiseCashStrategy(_SingleSeedStrategy):
    strategy_id = "raise_cash_v1"
    objective = "RAISE_CASH"
    label = "Raise cash"
    summary = "Generate a cash-raising candidate seeded from the baseline proposal."


class LowerTurnoverStrategy(_SingleSeedStrategy):
    strategy_id = "lower_turnover_v1"
    objective = "LOWER_TURNOVER"
    label = "Lower turnover"
    summary = "Generate a lower-turnover candidate seeded from current intent and holding posture."


class ImproveCurrencyAlignmentStrategy(_SingleSeedStrategy):
    strategy_id = "improve_currency_alignment_v1"
    objective = "IMPROVE_CURRENCY_ALIGNMENT"
    label = "Improve currency alignment"
    summary = "Generate a currency-alignment candidate bounded by allowed currency constraints."


class AvoidRestrictedProductsStrategy(_SingleSeedStrategy):
    strategy_id = "avoid_restricted_products_v1"
    objective = "AVOID_RESTRICTED_PRODUCTS"
    label = "Avoid restricted products"
    summary = (
        "Generate a restricted-product avoidance candidate when canonical evidence is available."
    )
    required_evidence = ("RESTRICTED_PRODUCT_ELIGIBILITY", "MANDATE_CONTEXT")


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


def build_candidate_seeds(
    *,
    request: NormalizedProposalAlternativesRequest,
    inputs: AlternativeStrategyInputs,
    registry: dict[AlternativeConstructionObjective, AlternativeConstructionStrategy] | None = None,
) -> tuple[AlternativeCandidateSeed, ...]:
    strategies = registry or build_initial_strategy_registry()
    seeds: list[AlternativeCandidateSeed] = []
    for objective in request.requested_objectives:
        strategy = strategies.get(objective)
        if strategy is None:
            continue
        seeds.extend(strategy.build_seeds(request=request, inputs=inputs))
    return tuple(seeds)


def _candidate_id(*, objective: str, portfolio_id: str, pivot: str) -> str:
    return f"alt_{objective.lower()}_{portfolio_id.lower()}_{pivot.lower()}"


def _first_value(values: Iterable[str]) -> str | None:
    for value in values:
        if value:
            return value
    return None
