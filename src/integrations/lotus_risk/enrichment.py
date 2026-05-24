from __future__ import annotations

import os
import time
from decimal import Decimal
from typing import Any, cast

import httpx
from pydantic import BaseModel, Field, ValidationError

from src.core.models import (
    PositionSummary,
    ProposalResult,
    ProposalSimulateRequest,
    SecurityTradeIntent,
    ShelfEntry,
)
from src.integrations.lotus_core.runtime_config import env_positive_float, env_positive_int

_CONCENTRATION_PATH = "/analytics/risk/concentration"


class LotusRiskEnrichmentUnavailableError(Exception):
    pass


class LotusRiskConcentrationRiskProxy(BaseModel):
    hhi_current: Decimal
    hhi_proposed: Decimal
    hhi_delta: Decimal


class LotusRiskPositionDescriptor(BaseModel):
    security_id: str | None = None
    security_name: str | None = None
    weight: Decimal


class LotusRiskIssuerDescriptor(BaseModel):
    issuer_id: str | None = None
    issuer_name: str | None = None
    weight: Decimal


class LotusRiskSinglePositionConcentration(BaseModel):
    top_position_weight_current: Decimal
    top_position_weight_proposed: Decimal
    top_position_weight_delta: Decimal
    top_n_cumulative_weight_current: Decimal
    top_n_cumulative_weight_proposed: Decimal
    top_n_cumulative_weight_delta: Decimal
    top_n: int
    top_position_current: LotusRiskPositionDescriptor | None = None
    top_position_proposed: LotusRiskPositionDescriptor | None = None


class LotusRiskIssuerConcentration(BaseModel):
    hhi_current: Decimal
    hhi_proposed: Decimal
    hhi_delta: Decimal
    top_issuer_weight_current: Decimal
    top_issuer_weight_proposed: Decimal
    top_issuer_weight_delta: Decimal
    coverage_status: str
    coverage_ratio_current: Decimal | None = None
    coverage_ratio_proposed: Decimal | None = None
    covered_position_count_current: int
    covered_position_count_proposed: int
    total_position_count_current: int
    total_position_count_proposed: int
    uncovered_position_count_current: int | None = None
    uncovered_position_count_proposed: int | None = None
    top_issuer_current: LotusRiskIssuerDescriptor | None = None
    top_issuer_proposed: LotusRiskIssuerDescriptor | None = None
    note: str | None = None


class LotusRiskConcentrationResponse(BaseModel):
    source_service: str = Field(pattern="^lotus-risk$")
    input_mode: str = Field(pattern="^(simulation|stateless)$")
    risk_proxy: LotusRiskConcentrationRiskProxy
    single_position_concentration: LotusRiskSinglePositionConcentration
    issuer_concentration: LotusRiskIssuerConcentration
    valuation_context: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


def _resolve_base_url() -> str:
    configured = os.getenv("LOTUS_RISK_BASE_URL")
    if configured:
        return configured.rstrip("/")
    raise LotusRiskEnrichmentUnavailableError("LOTUS_RISK_ENRICHMENT_UNAVAILABLE")


def _resolve_timeout() -> httpx.Timeout:
    return httpx.Timeout(env_positive_float("LOTUS_RISK_TIMEOUT_SECONDS", default=10.0))


def _resolve_retry_attempts() -> int:
    attempts = env_positive_int("LOTUS_RISK_RETRY_ATTEMPTS", default=2)
    return min(int(attempts), 5)


def _is_retryable_http_error(exc: httpx.HTTPError) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return bool(status_code >= 500 or status_code == 429)
    return True


def _request_concentration_response(
    *,
    payload: dict[str, Any],
    correlation_id: str,
) -> LotusRiskConcentrationResponse:
    attempts = _resolve_retry_attempts()
    last_error: Exception | None = None
    with httpx.Client(timeout=_resolve_timeout()) as client:
        for attempt in range(1, attempts + 1):
            try:
                response = client.post(
                    f"{_resolve_base_url()}{_CONCENTRATION_PATH}",
                    json=payload,
                    headers={"X-Correlation-Id": correlation_id},
                )
                response.raise_for_status()
                body = cast(dict[str, Any], response.json())
                concentration = cast(
                    LotusRiskConcentrationResponse,
                    LotusRiskConcentrationResponse.model_validate(body),
                )
                return concentration
            except ValidationError as exc:
                raise LotusRiskEnrichmentUnavailableError(
                    "LOTUS_RISK_ENRICHMENT_UNAVAILABLE"
                ) from exc
            except ValueError as exc:
                raise LotusRiskEnrichmentUnavailableError(
                    "LOTUS_RISK_ENRICHMENT_UNAVAILABLE"
                ) from exc
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt >= attempts or not _is_retryable_http_error(exc):
                    break
                time.sleep(_retry_delay_seconds(attempt=attempt))
    raise LotusRiskEnrichmentUnavailableError("LOTUS_RISK_ENRICHMENT_UNAVAILABLE") from last_error


def _json_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _resolve_retry_backoff_seconds() -> Any:
    return min(env_positive_float("LOTUS_RISK_RETRY_BACKOFF_SECONDS", default=0.1), 2.0)


def _retry_delay_seconds(*, attempt: int) -> Any:
    return min(_resolve_retry_backoff_seconds() * attempt, 2.0)


def _shelf_by_instrument(request: ProposalSimulateRequest) -> dict[str, ShelfEntry]:
    return {entry.instrument_id: entry for entry in request.shelf_entries}


def _position_identity(position: PositionSummary) -> dict[str, Any]:
    return {
        "security_id": position.instrument_id,
        "security_name": position.instrument_id,
    }


def _issuer_fields(position: PositionSummary, shelf: dict[str, ShelfEntry]) -> dict[str, Any]:
    entry = shelf.get(position.instrument_id)
    if entry is None:
        return {}
    return {
        key: value
        for key, value in {
            "issuer_id": entry.issuer_id,
            "ultimate_parent_issuer_id": entry.attributes.get("ultimate_parent_issuer_id"),
        }.items()
        if value is not None
    }


def _current_concentration_position(
    position: PositionSummary,
    *,
    shelf: dict[str, ShelfEntry],
) -> dict[str, Any]:
    return {
        **_position_identity(position),
        "quantity": _json_decimal(position.quantity),
        "market_value_base": _json_decimal(position.value_in_base_ccy.amount),
        "weight": _json_decimal(position.weight),
        **_issuer_fields(position, shelf),
    }


def _projected_concentration_position(
    position: PositionSummary,
    *,
    shelf: dict[str, ShelfEntry],
) -> dict[str, Any]:
    return {
        **_position_identity(position),
        "proposed_quantity": _json_decimal(position.quantity),
        "projected_market_value_base": _json_decimal(position.value_in_base_ccy.amount),
        "projected_weight": _json_decimal(position.weight),
        **_issuer_fields(position, shelf),
    }


def _current_cash_concentration_positions(proposal_result: ProposalResult) -> list[dict[str, Any]]:
    total_value = proposal_result.before.total_value.amount
    positions: list[dict[str, Any]] = []
    for cash_balance in proposal_result.before.cash_balances:
        positions.append(
            _cash_concentration_position(
                currency=cash_balance.currency,
                amount=cash_balance.amount,
                total_value=total_value,
                projected=False,
            )
        )
    return positions


def _projected_cash_concentration_positions(
    proposal_result: ProposalResult,
) -> list[dict[str, Any]]:
    total_value = proposal_result.after_simulated.total_value.amount
    positions: list[dict[str, Any]] = []
    for cash_balance in proposal_result.after_simulated.cash_balances:
        positions.append(
            _cash_concentration_position(
                currency=cash_balance.currency,
                amount=cash_balance.amount,
                total_value=total_value,
                projected=True,
            )
        )
    return positions


def _cash_concentration_position(
    *,
    currency: str,
    amount: Decimal,
    total_value: Decimal,
    projected: bool,
) -> dict[str, Any]:
    security_id = f"CASH_{currency}"
    weight = Decimal("0") if total_value == 0 else amount / total_value
    common = {
        "security_id": security_id,
        "security_name": f"{currency} Cash",
        "issuer_id": security_id,
        "ultimate_parent_issuer_id": security_id,
    }
    if projected:
        return {
            **common,
            "proposed_quantity": _json_decimal(amount),
            "projected_market_value_base": _json_decimal(amount),
            "projected_weight": _json_decimal(weight),
        }
    return {
        **common,
        "quantity": _json_decimal(amount),
        "market_value_base": _json_decimal(amount),
        "weight": _json_decimal(weight),
    }


def _security_trade_changes(result: ProposalResult) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for intent in result.intents:
        if not isinstance(intent, SecurityTradeIntent):
            continue
        change: dict[str, Any] = {
            "security_id": intent.instrument_id,
            "transaction_type": intent.side,
            "quantity": _json_decimal(intent.quantity),
            "metadata": {
                "proposal_intent_id": intent.intent_id,
                "proposal_intent_type": intent.intent_type,
            },
        }
        if intent.notional is not None:
            change["amount"] = _json_decimal(intent.notional.amount)
            change["currency"] = intent.notional.currency
        changes.append({key: value for key, value in change.items() if value is not None})
    return changes


def _issuer_mappings(
    request: ProposalSimulateRequest,
    proposal_result: ProposalResult,
) -> list[dict[str, Any]]:
    changed_instruments = {
        intent.instrument_id
        for intent in proposal_result.intents
        if isinstance(intent, SecurityTradeIntent)
    }
    if not changed_instruments:
        return []

    mappings: list[dict[str, Any]] = []
    for shelf_entry in request.shelf_entries:
        if shelf_entry.instrument_id not in changed_instruments or shelf_entry.issuer_id is None:
            continue
        mapping = {
            "security_id": shelf_entry.instrument_id,
            "issuer_id": shelf_entry.issuer_id,
            "issuer_name": shelf_entry.attributes.get("issuer_name"),
            "ultimate_parent_issuer_id": shelf_entry.attributes.get("ultimate_parent_issuer_id"),
            "ultimate_parent_issuer_name": shelf_entry.attributes.get(
                "ultimate_parent_issuer_name"
            ),
        }
        mappings.append({key: value for key, value in mapping.items() if value is not None})
    return mappings


def _build_simulation_concentration_request(
    *,
    request: ProposalSimulateRequest,
    proposal_result: ProposalResult,
    resolved_as_of: str,
) -> dict[str, Any]:
    simulation_input: dict[str, Any] = {
        "portfolio_id": request.portfolio_snapshot.portfolio_id,
        "as_of_date": resolved_as_of,
        "reporting_currency": request.portfolio_snapshot.base_currency,
        "include_cash_positions": True,
        "include_zero_quantity_positions": False,
        "top_n": 10,
        "simulation_changes": _security_trade_changes(proposal_result),
    }
    issuer_mappings = _issuer_mappings(request, proposal_result)
    if issuer_mappings:
        simulation_input["issuer_mappings"] = issuer_mappings
    return {
        "input_mode": "simulation",
        "simulation_input": simulation_input,
        "issuer_grouping_level": "ultimate_parent",
        "enrichment_policy": "merge_caller_then_core",
    }


def _build_stateless_concentration_request(
    *,
    request: ProposalSimulateRequest,
    proposal_result: ProposalResult,
) -> dict[str, Any]:
    shelf = _shelf_by_instrument(request)
    stateless_input: dict[str, Any] = {
        "current_positions": [
            _current_concentration_position(position, shelf=shelf)
            for position in proposal_result.before.positions
        ]
        + _current_cash_concentration_positions(proposal_result),
        "projected_positions": [
            _projected_concentration_position(position, shelf=shelf)
            for position in proposal_result.after_simulated.positions
        ]
        + _projected_cash_concentration_positions(proposal_result),
        "top_n": 10,
    }
    return {
        "input_mode": "stateless",
        "stateless_input": stateless_input,
        "issuer_grouping_level": "ultimate_parent",
        "enrichment_policy": "use_caller_only",
    }


def _build_concentration_request(
    *,
    request: ProposalSimulateRequest,
    proposal_result: ProposalResult,
    resolved_as_of: str | None,
    input_mode: str | None,
) -> dict[str, Any]:
    if input_mode == "stateful" and resolved_as_of is not None:
        return _build_simulation_concentration_request(
            request=request,
            proposal_result=proposal_result,
            resolved_as_of=resolved_as_of,
        )
    return _build_stateless_concentration_request(
        request=request,
        proposal_result=proposal_result,
    )


def _apply_concentration_response(
    *,
    proposal_result: ProposalResult,
    concentration: LotusRiskConcentrationResponse,
) -> ProposalResult:
    explanation = dict(proposal_result.explanation)
    explanation["risk_lens"] = {
        "source_service": concentration.source_service,
        "input_mode": concentration.input_mode,
        "risk_proxy": concentration.risk_proxy.model_dump(mode="json"),
        "single_position_concentration": (
            concentration.single_position_concentration.model_dump(mode="json")
        ),
        "issuer_concentration": concentration.issuer_concentration.model_dump(mode="json"),
        "valuation_context": concentration.valuation_context,
        "metadata": concentration.metadata,
    }
    proposal_result.explanation = explanation
    return proposal_result


def enrich_with_lotus_risk(
    *,
    request: ProposalSimulateRequest,
    proposal_result: ProposalResult,
    correlation_id: str,
    resolved_as_of: str | None = None,
    input_mode: str | None = None,
) -> ProposalResult:
    payload = _build_concentration_request(
        request=request,
        proposal_result=proposal_result,
        resolved_as_of=resolved_as_of,
        input_mode=input_mode,
    )
    concentration = _request_concentration_response(
        payload=payload,
        correlation_id=correlation_id,
    )
    return _apply_concentration_response(
        proposal_result=proposal_result,
        concentration=concentration,
    )
