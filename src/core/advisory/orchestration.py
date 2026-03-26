from src.core.advisory_engine import run_proposal_simulation
from src.core.models import ProposalResult, ProposalSimulateRequest
from src.integrations.lotus_core import (
    LotusCoreSimulationUnavailableError,
    build_lotus_core_dependency_state,
    simulate_with_lotus_core,
)
from src.integrations.lotus_risk import (
    LotusRiskEnrichmentUnavailableError,
    build_lotus_risk_dependency_state,
    enrich_with_lotus_risk,
)


def evaluate_advisory_proposal(
    *,
    request: ProposalSimulateRequest,
    request_hash: str,
    idempotency_key: str | None,
    correlation_id: str,
) -> ProposalResult:
    degraded_reasons: list[str] = []

    lotus_core_state = build_lotus_core_dependency_state()
    simulation_authority = "lotus_advise_local"
    try:
        proposal_result = simulate_with_lotus_core(
            request=request,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        simulation_authority = "lotus_core"
    except LotusCoreSimulationUnavailableError:
        if lotus_core_state.configured:
            degraded_reasons.append("LOTUS_CORE_SIMULATION_UNAVAILABLE")
        proposal_result = run_proposal_simulation(
            portfolio=request.portfolio_snapshot,
            market_data=request.market_data_snapshot,
            shelf=request.shelf_entries,
            options=request.options,
            proposed_cash_flows=request.proposed_cash_flows,
            proposed_trades=request.proposed_trades,
            reference_model=request.reference_model,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )

    lotus_risk_state = build_lotus_risk_dependency_state()
    risk_authority = "lotus_advise_local"
    try:
        proposal_result = enrich_with_lotus_risk(
            request=request,
            proposal_result=proposal_result,
            correlation_id=correlation_id,
        )
        risk_authority = "lotus_risk"
    except LotusRiskEnrichmentUnavailableError:
        if lotus_risk_state.configured:
            degraded_reasons.append("LOTUS_RISK_ENRICHMENT_UNAVAILABLE")

    explanation = dict(proposal_result.explanation)
    explanation["authority_resolution"] = {
        "simulation_authority": simulation_authority,
        "risk_authority": risk_authority,
        "degraded": bool(degraded_reasons),
        "degraded_reasons": degraded_reasons,
    }

    proposal_result.explanation = explanation
    return proposal_result
