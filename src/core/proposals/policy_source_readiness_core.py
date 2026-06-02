from __future__ import annotations

from typing import Any

from src.core.proposals.source_readiness_common import (
    ReadinessStatus,
    list_at,
    source_readiness_section,
)


def build_core_policy_source_sections(
    *,
    advisory_policy_context: dict[str, Any],
    resolution_source: str,
    portfolio_snapshot: dict[str, Any],
    prices: list[Any],
    fx_rates: list[Any],
) -> list[dict[str, Any]]:
    return [
        source_readiness_section(
            key="core_client_profile_classification",
            owner_service="lotus-core",
            status=_client_profile_status(advisory_policy_context),
            evidence_refs=[
                "context_resolution.advisory_policy_context.household_id",
                "context_resolution.advisory_policy_context.jurisdiction",
                "context_resolution.resolved_context",
            ],
            missing_evidence=_client_profile_missing(advisory_policy_context),
            reason_codes=_client_profile_reasons(advisory_policy_context),
        ),
        source_readiness_section(
            key="core_mandate_objectives_restrictions",
            owner_service="lotus-core",
            status=_mandate_status(advisory_policy_context),
            evidence_refs=[
                "context_resolution.advisory_policy_context.mandate_id",
                "context_resolution.resolved_context",
            ],
            missing_evidence=_mandate_missing(advisory_policy_context),
            reason_codes=_mandate_reasons(advisory_policy_context),
        ),
        source_readiness_section(
            key="core_holdings_cash_market_data",
            owner_service="lotus-core",
            status=_holdings_market_status(
                resolution_source=resolution_source,
                portfolio_snapshot=portfolio_snapshot,
                prices=prices,
                fx_rates=fx_rates,
            ),
            evidence_refs=[
                "inputs.portfolio_snapshot.positions",
                "inputs.portfolio_snapshot.cash_balances",
                "inputs.market_data_snapshot.prices",
                "inputs.market_data_snapshot.fx_rates",
            ],
            missing_evidence=_holdings_market_missing(
                resolution_source=resolution_source,
                portfolio_snapshot=portfolio_snapshot,
                prices=prices,
                fx_rates=fx_rates,
            ),
            reason_codes=_holdings_market_reasons(
                resolution_source=resolution_source,
                portfolio_snapshot=portfolio_snapshot,
                prices=prices,
                fx_rates=fx_rates,
            ),
        ),
    ]


def _client_profile_status(policy_context: dict[str, Any]) -> ReadinessStatus:
    missing = _client_profile_missing(policy_context)
    if not missing:
        return "READY"
    required = {"household_id", "jurisdiction"}
    return "BLOCKED" if required.issubset(set(missing)) else "PENDING_REVIEW"


def _client_profile_missing(policy_context: dict[str, Any]) -> list[str]:
    missing = []
    for key in (
        "household_id",
        "jurisdiction",
        "client_classification",
        "booking_center_code",
        "account_id",
        "time_horizon",
        "liquidity_need",
    ):
        if not policy_context.get(key):
            missing.append(key)
    return missing


def _client_profile_reasons(policy_context: dict[str, Any]) -> list[str]:
    return [f"CORE_{key.upper()}_NOT_PROVIDED" for key in _client_profile_missing(policy_context)]


def _mandate_status(policy_context: dict[str, Any]) -> ReadinessStatus:
    missing = _mandate_missing(policy_context)
    if not missing:
        return "READY"
    return "BLOCKED" if "mandate_id" in missing else "PENDING_REVIEW"


def _mandate_missing(policy_context: dict[str, Any]) -> list[str]:
    missing = []
    for key in ("mandate_id", "objectives", "restrictions"):
        if not policy_context.get(key):
            missing.append(key)
    return missing


def _mandate_reasons(policy_context: dict[str, Any]) -> list[str]:
    return [f"CORE_{key.upper()}_NOT_PROVIDED" for key in _mandate_missing(policy_context)]


def _holdings_market_status(
    *,
    resolution_source: str,
    portfolio_snapshot: dict[str, Any],
    prices: list[Any],
    fx_rates: list[Any],
) -> ReadinessStatus:
    missing = _holdings_market_missing(
        resolution_source=resolution_source,
        portfolio_snapshot=portfolio_snapshot,
        prices=prices,
        fx_rates=fx_rates,
    )
    blocking = {"positions", "price rows"}
    if blocking.intersection(missing):
        return "BLOCKED"
    return "READY" if not missing else "PENDING_REVIEW"


def _holdings_market_missing(
    *,
    resolution_source: str,
    portfolio_snapshot: dict[str, Any],
    prices: list[Any],
    fx_rates: list[Any],
) -> list[str]:
    missing = []
    if resolution_source != "LOTUS_CORE":
        missing.append("lotus-core authoritative context resolution")
    if not list_at(portfolio_snapshot, "positions"):
        missing.append("positions")
    if not list_at(portfolio_snapshot, "cash_balances"):
        missing.append("cash_balances")
    if not prices:
        missing.append("price rows")
    if not fx_rates:
        missing.append("FX rate rows")
    return missing


def _holdings_market_reasons(
    *,
    resolution_source: str,
    portfolio_snapshot: dict[str, Any],
    prices: list[Any],
    fx_rates: list[Any],
) -> list[str]:
    reasons = []
    if resolution_source != "LOTUS_CORE":
        reasons.append("DIRECT_REQUEST_NOT_SOURCE_OWNER")
    if not list_at(portfolio_snapshot, "positions"):
        reasons.append("CORE_POSITIONS_NOT_PROVIDED")
    if not list_at(portfolio_snapshot, "cash_balances"):
        reasons.append("CORE_CASH_NOT_PROVIDED")
    if not prices:
        reasons.append("CORE_PRICE_NOT_PROVIDED")
    if not fx_rates:
        reasons.append("CORE_FX_RATE_NOT_PROVIDED")
    return reasons
