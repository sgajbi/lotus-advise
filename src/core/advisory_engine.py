from typing import Any, Optional

from src.core.advisory.ids import proposal_run_id_from_request_hash
from src.core.advisory.simulation_decision_support import build_simulation_decision_support
from src.core.advisory.simulation_intent_plan import build_simulation_intent_plan
from src.core.advisory.simulation_review import evaluate_simulation_review
from src.core.common.diagnostics import make_diagnostics_data
from src.core.common.idempotency import normalize_optional_idempotency_key
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
from src.core.source_provenance_models import SourceProvenanceEnvelope
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

    decision_support = build_simulation_decision_support(
        portfolio=portfolio,
        market_data=market_data,
        shelf=shelf,
        options=options,
        diagnostics=diagnostics,
        before=before,
        after=after,
        intent_plan=intent_plan,
        final_status=review.final_status,
        rule_results=review.rule_results,
        reference_model=reference_model_validated,
        policy_context=policy_context,
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
        drift_analysis=decision_support.drift_analysis,
        suitability=decision_support.suitability,
        gate_decision=decision_support.gate_decision,
        explanation={"summary": review.final_status},
        lineage=LineageData(
            portfolio_snapshot_id=portfolio.snapshot_id or portfolio.portfolio_id,
            market_data_snapshot_id=market_data.snapshot_id or "md",
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            engine_version="0.1.0",
            simulation_contract_version=simulation_contract_version,
            source_provenance=_source_provenance_envelope(
                portfolio=portfolio,
                market_data=market_data,
            ),
        ),
    )


def _source_provenance_envelope(
    *,
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
) -> SourceProvenanceEnvelope | None:
    if portfolio.source_provenance is None or market_data.source_provenance is None:
        return None
    source_system = portfolio.source_provenance.source_system
    if market_data.source_provenance.source_system != source_system:
        return None
    return SourceProvenanceEnvelope(
        source_system=source_system,
        portfolio=portfolio.source_provenance,
        market_data=market_data.source_provenance,
    )
