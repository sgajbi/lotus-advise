"""Post-trade Rule Engine implementation (RFC-0005/RFC-0006B)."""

from src.core.compliance_rules import (
    evaluate_cash_band,
    evaluate_data_quality,
    evaluate_min_trade_size,
    evaluate_no_shorting,
    evaluate_single_position_max,
    evaluate_sufficient_cash,
)
from src.core.diagnostics_models import DiagnosticsData, RuleResult
from src.core.engine_options_models import EngineOptions
from src.core.simulation_state_models import SimulatedState


class RuleEngine:
    """
    Evaluates business rules against the simulated after-state.
    Supports HARD (Block), SOFT (Review), and INFO (Log) severities.
    Enforces RFC-0006B: All core rules must emit a result.
    """

    @staticmethod
    def evaluate(
        state: SimulatedState, options: EngineOptions, diagnostics: DiagnosticsData
    ) -> list[RuleResult]:
        return [
            evaluate_cash_band(state, options),
            *evaluate_single_position_max(state, options),
            evaluate_data_quality(options, diagnostics),
            evaluate_min_trade_size(diagnostics),
            evaluate_no_shorting(state),
            evaluate_sufficient_cash(state),
        ]
