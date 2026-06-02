from dataclasses import dataclass
from typing import Any, Literal

from src.core.advisory.simulation_intent_plan import SimulationIntentPlan
from src.core.common.drift_analytics import compute_drift_analysis
from src.core.common.suitability import compute_suitability_result
from src.core.common.workflow_gates import evaluate_gate_decision
from src.core.diagnostics_models import DiagnosticsData, RuleResult
from src.core.drift_models import DriftAnalysis
from src.core.engine_options_models import EngineOptions
from src.core.gate_models import GateDecision
from src.core.portfolio_models import (
    MarketDataSnapshot,
    PortfolioSnapshot,
    ReferenceModel,
    ShelfEntry,
)
from src.core.simulation_state_models import SimulatedState
from src.core.suitability_models import SuitabilityResult


@dataclass(frozen=True)
class SimulationDecisionSupport:
    drift_analysis: DriftAnalysis | None
    suitability: SuitabilityResult | None
    gate_decision: GateDecision | None


def build_simulation_decision_support(
    *,
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: list[ShelfEntry],
    options: EngineOptions,
    diagnostics: DiagnosticsData,
    before: SimulatedState,
    after: SimulatedState,
    intent_plan: SimulationIntentPlan,
    final_status: Literal["READY", "BLOCKED", "PENDING_REVIEW"],
    rule_results: list[RuleResult],
    reference_model: ReferenceModel | None,
    policy_context: dict[str, Any] | None,
) -> SimulationDecisionSupport:
    drift_analysis = _build_drift_analysis(
        portfolio=portfolio,
        options=options,
        diagnostics=diagnostics,
        before=before,
        after=after,
        intent_plan=intent_plan,
        reference_model=reference_model,
    )
    suitability = _build_suitability(
        portfolio=portfolio,
        market_data=market_data,
        shelf=shelf,
        options=options,
        before=before,
        after=after,
        intent_plan=intent_plan,
        policy_context=policy_context,
    )
    gate_decision = _build_gate_decision(
        options=options,
        diagnostics=diagnostics,
        final_status=final_status,
        rule_results=rule_results,
        suitability=suitability,
    )

    return SimulationDecisionSupport(
        drift_analysis=drift_analysis,
        suitability=suitability,
        gate_decision=gate_decision,
    )


def _build_drift_analysis(
    *,
    portfolio: PortfolioSnapshot,
    options: EngineOptions,
    diagnostics: DiagnosticsData,
    before: SimulatedState,
    after: SimulatedState,
    intent_plan: SimulationIntentPlan,
    reference_model: ReferenceModel | None,
) -> DriftAnalysis | None:
    if not options.enable_drift_analytics or reference_model is None:
        return None
    if reference_model.base_currency != portfolio.base_currency:
        diagnostics.warnings.append("REFERENCE_MODEL_BASE_CURRENCY_MISMATCH")
        return None

    traded_instruments = {
        intent.instrument_id
        for intent in intent_plan.intents
        if intent.intent_type == "SECURITY_TRADE"
    }
    return compute_drift_analysis(
        before=before,
        after=after,
        reference_model=reference_model,
        traded_instruments=traded_instruments,
        options=options,
    )


def _build_suitability(
    *,
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: list[ShelfEntry],
    options: EngineOptions,
    before: SimulatedState,
    after: SimulatedState,
    intent_plan: SimulationIntentPlan,
    policy_context: dict[str, Any] | None,
) -> SuitabilityResult | None:
    if not options.enable_suitability_scanner:
        return None
    return compute_suitability_result(
        before=before,
        after=after,
        shelf=shelf,
        options=options,
        portfolio_snapshot_id=portfolio.snapshot_id or portfolio.portfolio_id,
        market_data_snapshot_id=market_data.snapshot_id or "md",
        proposed_trades=intent_plan.trades,
        policy_context=policy_context,
    )


def _build_gate_decision(
    *,
    options: EngineOptions,
    diagnostics: DiagnosticsData,
    final_status: Literal["READY", "BLOCKED", "PENDING_REVIEW"],
    rule_results: list[RuleResult],
    suitability: SuitabilityResult | None,
) -> GateDecision | None:
    if not options.enable_workflow_gates:
        return None
    return evaluate_gate_decision(
        status=final_status,
        rule_results=rule_results,
        suitability=suitability,
        diagnostics=diagnostics,
        options=options,
        default_requires_client_consent=True,
    )
