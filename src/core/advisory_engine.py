from typing import Any, Optional

from src.core.advisory.ids import proposal_run_id_from_request_hash
from src.core.advisory.simulation_intent_plan import build_simulation_intent_plan
from src.core.advisory.simulation_review import evaluate_simulation_review
from src.core.common.diagnostics import make_diagnostics_data
from src.core.common.drift_analytics import compute_drift_analysis
from src.core.common.idempotency import normalize_optional_idempotency_key
from src.core.common.suitability import compute_suitability_result
from src.core.common.workflow_gates import evaluate_gate_decision
from src.core.diagnostics_models import LineageData
from src.core.engine_options_models import EngineOptions, ValuationMode
from src.core.portfolio_models import (
    MarketDataSnapshot,
    PortfolioSnapshot,
    ReferenceModel,
    ShelfEntry,
)
from src.core.proposal_request_models import ProposedCashFlow, ProposedTrade
from src.core.proposal_result_models import ProposalResult
from src.core.valuation import build_simulated_state


def run_proposal_simulation(
    *,
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: list[ShelfEntry],
    options: EngineOptions,
    proposed_cash_flows: list[ProposedCashFlow] | list[dict[str, Any]],
    proposed_trades: list[ProposedTrade] | list[dict[str, Any]],
    reference_model: Optional[ReferenceModel | dict[str, Any]] = None,
    request_hash: str = "no_hash",
    idempotency_key: Optional[str] = None,
    correlation_id: str = "c_none",
    simulation_contract_version: Optional[str] = None,
    policy_context: Optional[dict[str, Any]] = None,
) -> ProposalResult:
    idempotency_key = normalize_optional_idempotency_key(idempotency_key)
    run_id = proposal_run_id_from_request_hash(request_hash)
    diagnostics = make_diagnostics_data()

    before = build_simulated_state(
        portfolio,
        market_data,
        shelf,
        diagnostics.data_quality,
        diagnostics.warnings,
        options,
    )
    reference_model_validated = (
        ReferenceModel.model_validate(reference_model) if reference_model is not None else None
    )
    intent_plan = build_simulation_intent_plan(
        portfolio=portfolio,
        market_data=market_data,
        shelf=shelf,
        options=options,
        proposed_cash_flows=proposed_cash_flows,
        proposed_trades=proposed_trades,
        diagnostics=diagnostics,
    )

    if intent_plan.intents:
        after = build_simulated_state(
            intent_plan.after_portfolio,
            market_data,
            shelf,
            diagnostics.data_quality,
            diagnostics.warnings,
            options.model_copy(update={"valuation_mode": ValuationMode.CALCULATED}),
        )
    else:
        after = before.model_copy(deep=True)
    review = evaluate_simulation_review(
        portfolio=portfolio,
        market_data=market_data,
        options=options,
        diagnostics=diagnostics,
        before=before,
        after=after,
        intent_plan=intent_plan,
    )

    drift_analysis = None
    if options.enable_drift_analytics and reference_model_validated is not None:
        if reference_model_validated.base_currency != portfolio.base_currency:
            diagnostics.warnings.append("REFERENCE_MODEL_BASE_CURRENCY_MISMATCH")
        else:
            traded_instruments = {
                intent.instrument_id
                for intent in intent_plan.intents
                if intent.intent_type == "SECURITY_TRADE"
            }
            drift_analysis = compute_drift_analysis(
                before=before,
                after=after,
                reference_model=reference_model_validated,
                traded_instruments=traded_instruments,
                options=options,
            )

    suitability = None
    if options.enable_suitability_scanner:
        suitability = compute_suitability_result(
            before=before,
            after=after,
            shelf=shelf,
            options=options,
            portfolio_snapshot_id=portfolio.snapshot_id or portfolio.portfolio_id,
            market_data_snapshot_id=market_data.snapshot_id or "md",
            proposed_trades=intent_plan.trades,
            policy_context=policy_context,
        )
    gate_decision = None
    if options.enable_workflow_gates:
        gate_decision = evaluate_gate_decision(
            status=review.final_status,
            rule_results=review.rule_results,
            suitability=suitability,
            diagnostics=diagnostics,
            options=options,
            default_requires_client_consent=True,
        )

    return ProposalResult(
        proposal_run_id=run_id,
        correlation_id=correlation_id,
        status=review.final_status,
        before=before,
        intents=intent_plan.intents,
        after_simulated=after,
        reconciliation=review.reconciliation,
        rule_results=review.rule_results,
        diagnostics=diagnostics,
        drift_analysis=drift_analysis,
        suitability=suitability,
        gate_decision=gate_decision,
        explanation={"summary": review.final_status},
        lineage=LineageData(
            portfolio_snapshot_id=portfolio.snapshot_id or portfolio.portfolio_id,
            market_data_snapshot_id=market_data.snapshot_id or "md",
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            engine_version="0.1.0",
            simulation_contract_version=simulation_contract_version,
        ),
    )
