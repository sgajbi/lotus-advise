from src.core.advisory.alternatives_normalizer import NormalizedProposalAlternativesRequest
from src.core.advisory.alternatives_strategy_base import BaseAlternativeStrategy
from src.core.advisory.alternatives_strategy_models import (
    AlternativeStrategyBuildResult,
    AlternativeStrategyInputs,
)
from src.core.advisory.alternatives_strategy_support import (
    first_adjustable_trade,
    reduced_trade_payload,
)


class LowerTurnoverStrategy(BaseAlternativeStrategy):
    strategy_id = "lower_turnover_v1"
    objective = "LOWER_TURNOVER"
    label = "Lower turnover"
    summary = "Reduce turnover by trimming baseline trades while preserving intent direction."

    def build_result(
        self,
        *,
        request: NormalizedProposalAlternativesRequest,
        inputs: AlternativeStrategyInputs,
    ) -> AlternativeStrategyBuildResult:
        baseline_trade = first_adjustable_trade(inputs.current_proposed_trades)
        if baseline_trade is None:
            return AlternativeStrategyBuildResult(
                rejected_candidates=(
                    self._reject(
                        inputs=inputs,
                        reason_code="ALTERNATIVE_BASELINE_TRADE_REQUIRED",
                        summary=(
                            "Lower-turnover alternatives require an existing baseline "
                            "trade to reduce."
                        ),
                        pivot=inputs.base_currency,
                        status="REJECTED_CONSTRAINT_VIOLATION",
                    ),
                )
            )

        reduced_trade = reduced_trade_payload(baseline_trade)
        if reduced_trade is None:
            return AlternativeStrategyBuildResult(
                rejected_candidates=(
                    self._reject(
                        inputs=inputs,
                        reason_code="ALTERNATIVE_BASELINE_TRADE_TOO_SMALL",
                        summary=(
                            "Baseline trade is too small to produce a lower-turnover alternative."
                        ),
                        pivot=baseline_trade.instrument_id,
                        status="REJECTED_CONSTRAINT_VIOLATION",
                    ),
                )
            )

        return AlternativeStrategyBuildResult(
            seeds=(
                self._seed(
                    request=request,
                    inputs=inputs,
                    pivot=baseline_trade.instrument_id,
                    generated_intents=[reduced_trade],
                    metadata={"baseline_trade_count": len(inputs.current_proposed_trades)},
                ),
            )
        )
