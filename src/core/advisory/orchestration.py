from dataclasses import dataclass
from typing import cast

from src.core.advisory.alternatives_projection import build_proposal_alternatives
from src.core.advisory.decision_summary import build_proposal_decision_summary
from src.core.advisory_engine import run_proposal_simulation
from src.core.common.idempotency import normalize_optional_idempotency_key
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposal_result_models import ProposalResult
from src.integrations.lotus_core import (
    LotusCoreSimulationUnavailableError,
    lotus_core_local_fallback_enabled,
    lotus_core_local_fallback_permitted,
    lotus_core_local_fallback_requested,
    simulate_with_lotus_core,
)
from src.integrations.lotus_risk import (
    LotusRiskEnrichmentUnavailableError,
    build_lotus_risk_dependency_state,
    enrich_with_lotus_risk,
)


@dataclass(frozen=True)
class _SimulationResolution:
    proposal_result: ProposalResult
    authority: str
    degraded_reasons: list[str]


@dataclass(frozen=True)
class _RiskResolution:
    proposal_result: ProposalResult
    authority: str
    degraded_reasons: list[str]


def evaluate_advisory_proposal(
    *,
    request: ProposalSimulateRequest,
    request_hash: str,
    idempotency_key: str | None,
    correlation_id: str,
    resolved_as_of: str | None = None,
    input_mode: str | None = None,
    policy_context: dict[str, object] | None = None,
) -> ProposalResult:
    idempotency_key = normalize_optional_idempotency_key(idempotency_key)
    simulation = _resolve_simulation(
        request=request,
        request_hash=request_hash,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        policy_context=policy_context,
    )
    risk = _resolve_risk_enrichment(
        request=request,
        proposal_result=simulation.proposal_result,
        correlation_id=correlation_id,
        resolved_as_of=resolved_as_of,
        input_mode=input_mode,
        degraded_reasons=simulation.degraded_reasons,
    )
    _attach_authority_explanation(
        proposal_result=risk.proposal_result,
        simulation_authority=simulation.authority,
        risk_authority=risk.authority,
        degraded_reasons=risk.degraded_reasons,
        policy_context=policy_context,
    )
    _attach_proposal_outputs(
        request=request,
        proposal_result=risk.proposal_result,
        correlation_id=correlation_id,
        resolved_as_of=resolved_as_of,
        policy_context=policy_context,
    )
    return cast(ProposalResult, risk.proposal_result)


def _resolve_simulation(
    *,
    request: ProposalSimulateRequest,
    request_hash: str,
    idempotency_key: str | None,
    correlation_id: str,
    policy_context: dict[str, object] | None,
) -> _SimulationResolution:
    try:
        return _SimulationResolution(
            proposal_result=simulate_with_lotus_core(
                request=request,
                request_hash=request_hash,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                policy_context=policy_context,
            ),
            authority="lotus_core",
            degraded_reasons=[],
        )
    except LotusCoreSimulationUnavailableError as exc:
        proposal_result = _run_local_fallback_simulation(
            request=request,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            policy_context=policy_context,
            original_error=exc,
        )
        return _SimulationResolution(
            proposal_result=proposal_result,
            authority="lotus_advise_local_fallback",
            degraded_reasons=["LOTUS_CORE_SIMULATION_UNAVAILABLE"],
        )


def _run_local_fallback_simulation(
    *,
    request: ProposalSimulateRequest,
    request_hash: str,
    idempotency_key: str | None,
    correlation_id: str,
    policy_context: dict[str, object] | None,
    original_error: LotusCoreSimulationUnavailableError,
) -> ProposalResult:
    if lotus_core_local_fallback_requested() and not lotus_core_local_fallback_permitted():
        raise LotusCoreSimulationUnavailableError(
            "LOTUS_CORE_SIMULATION_REQUIRED_IN_THIS_ENVIRONMENT",
            status_code=original_error.status_code,
        ) from original_error
    if not lotus_core_local_fallback_enabled():
        raise original_error

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
        simulation_contract_version="advisory-simulation.v1",
        policy_context=policy_context,
    )
    proposal_result.allocation_lens.source = "LOTUS_ADVISE_LOCAL_FALLBACK"
    return proposal_result


def _resolve_risk_enrichment(
    *,
    request: ProposalSimulateRequest,
    proposal_result: ProposalResult,
    correlation_id: str,
    resolved_as_of: str | None,
    input_mode: str | None,
    degraded_reasons: list[str],
) -> _RiskResolution:
    combined_degraded_reasons = list(degraded_reasons)
    lotus_risk_state = build_lotus_risk_dependency_state()
    try:
        proposal_result = enrich_with_lotus_risk(
            request=request,
            proposal_result=proposal_result,
            correlation_id=correlation_id,
            resolved_as_of=resolved_as_of,
            input_mode=input_mode,
        )
        return _RiskResolution(proposal_result, "lotus_risk", combined_degraded_reasons)
    except LotusRiskEnrichmentUnavailableError:
        if lotus_risk_state.configured:
            combined_degraded_reasons.append("LOTUS_RISK_ENRICHMENT_UNAVAILABLE")
        return _RiskResolution(proposal_result, "unavailable", combined_degraded_reasons)


def _attach_authority_explanation(
    *,
    proposal_result: ProposalResult,
    simulation_authority: str,
    risk_authority: str,
    degraded_reasons: list[str],
    policy_context: dict[str, object] | None,
) -> None:
    explanation = dict(proposal_result.explanation)
    explanation["authority_resolution"] = {
        "simulation_authority": simulation_authority,
        "risk_authority": risk_authority,
        "degraded": bool(degraded_reasons),
        "degraded_reasons": degraded_reasons,
    }
    if policy_context is not None:
        explanation["advisory_policy_context"] = dict(policy_context)

    proposal_result.explanation = explanation


def _attach_proposal_outputs(
    *,
    request: ProposalSimulateRequest,
    proposal_result: ProposalResult,
    correlation_id: str,
    resolved_as_of: str | None,
    policy_context: dict[str, object] | None,
) -> None:
    proposal_result.proposal_decision_summary = build_proposal_decision_summary(proposal_result)
    proposal_result.proposal_alternatives = build_proposal_alternatives(
        request=request,
        baseline_result=proposal_result,
        correlation_id=correlation_id,
        resolved_as_of=resolved_as_of,
        policy_context=policy_context,
    )
