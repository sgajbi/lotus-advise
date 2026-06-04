from __future__ import annotations

from typing import Any

from src.core.proposals.source_readiness_common import (
    ReadinessStatus,
    list_at,
    source_readiness_section,
)

_OPEN_END_VALUES = {"3999-12-31", "31-Dec-3999", "31-DEC-3999"}


def build_core_memo_source_sections(
    *,
    resolution_source: str,
    advisory_policy_context: dict[str, Any],
    portfolio_snapshot: dict[str, Any],
    prices: list[Any],
    fx_rates: list[Any],
    shelf_entries: list[Any],
    proposed_trades: list[Any],
) -> list[dict[str, Any]]:
    return [
        source_readiness_section(
            key="core_portfolio_holdings_cash",
            owner_service="lotus-core",
            status=_core_holdings_cash_status(
                resolution_source=resolution_source,
                portfolio_snapshot=portfolio_snapshot,
            ),
            evidence_refs=[
                "context_resolution.resolved_context.portfolio_snapshot_id",
                "inputs.portfolio_snapshot.positions",
                "inputs.portfolio_snapshot.cash_balances",
            ],
            missing_evidence=_missing_core_holdings_cash(
                resolution_source=resolution_source,
                portfolio_snapshot=portfolio_snapshot,
            ),
            reason_codes=_core_holdings_cash_reasons(
                resolution_source=resolution_source,
                portfolio_snapshot=portfolio_snapshot,
            ),
        ),
        source_readiness_section(
            key="core_household_account_mandate_objective_restrictions",
            owner_service="lotus-core",
            status=_client_context_status(advisory_policy_context),
            evidence_refs=[
                "context_resolution.advisory_policy_context.household_id",
                "context_resolution.advisory_policy_context.mandate_id",
                "context_resolution.resolved_context",
            ],
            missing_evidence=_missing_client_context(advisory_policy_context),
            reason_codes=_client_context_reasons(advisory_policy_context),
        ),
        source_readiness_section(
            key="core_market_prices",
            owner_service="lotus-core",
            status=_market_data_status(
                rows=prices,
                resolution_source=resolution_source,
                source_name="price",
            ),
            evidence_refs=[
                "context_resolution.resolved_context.market_data_snapshot_id",
                "inputs.market_data_snapshot.prices",
            ],
            missing_evidence=_market_data_missing(rows=prices, source_name="price"),
            reason_codes=_market_data_reasons(
                rows=prices,
                resolution_source=resolution_source,
                source_name="PRICE",
            ),
        ),
        source_readiness_section(
            key="core_fx_rates",
            owner_service="lotus-core",
            status=_market_data_status(
                rows=fx_rates,
                resolution_source=resolution_source,
                source_name="FX rate",
            ),
            evidence_refs=[
                "context_resolution.resolved_context.market_data_snapshot_id",
                "inputs.market_data_snapshot.fx_rates",
            ],
            missing_evidence=_market_data_missing(rows=fx_rates, source_name="FX rate"),
            reason_codes=_market_data_reasons(
                rows=fx_rates,
                resolution_source=resolution_source,
                source_name="FX_RATE",
            ),
        ),
        source_readiness_section(
            key="core_product_eligibility_complexity",
            owner_service="lotus-core",
            status=_product_source_status(
                shelf_entries=shelf_entries,
                proposed_trades=proposed_trades,
            ),
            evidence_refs=[
                "inputs.shelf_entries",
                "inputs.proposed_trades",
            ],
            missing_evidence=_product_source_missing(
                shelf_entries=shelf_entries,
                proposed_trades=proposed_trades,
            ),
            reason_codes=_product_source_reasons(
                shelf_entries=shelf_entries,
                proposed_trades=proposed_trades,
            ),
        ),
    ]


def _core_holdings_cash_status(
    *, resolution_source: str, portfolio_snapshot: dict[str, Any]
) -> ReadinessStatus:
    if not list_at(portfolio_snapshot, "positions") or not list_at(
        portfolio_snapshot, "cash_balances"
    ):
        return "BLOCKED"
    return "READY" if resolution_source == "LOTUS_CORE" else "PENDING_REVIEW"


def _missing_core_holdings_cash(
    *, resolution_source: str, portfolio_snapshot: dict[str, Any]
) -> list[str]:
    missing = []
    if resolution_source != "LOTUS_CORE":
        missing.append("lotus-core authoritative context resolution")
    if not list_at(portfolio_snapshot, "positions"):
        missing.append("positions")
    if not list_at(portfolio_snapshot, "cash_balances"):
        missing.append("cash_balances")
    return missing


def _core_holdings_cash_reasons(
    *, resolution_source: str, portfolio_snapshot: dict[str, Any]
) -> list[str]:
    reasons = []
    if resolution_source != "LOTUS_CORE":
        reasons.append("DIRECT_REQUEST_NOT_SOURCE_OWNER")
    if not list_at(portfolio_snapshot, "positions"):
        reasons.append("CORE_POSITIONS_NOT_PROVIDED")
    if not list_at(portfolio_snapshot, "cash_balances"):
        reasons.append("CORE_CASH_NOT_PROVIDED")
    return reasons


def _client_context_status(policy_context: dict[str, Any]) -> ReadinessStatus:
    missing = _missing_client_context(policy_context)
    if not missing:
        return "READY"
    return "BLOCKED" if {"household_id", "mandate_id"}.issubset(set(missing)) else "PENDING_REVIEW"


def _missing_client_context(policy_context: dict[str, Any]) -> list[str]:
    missing = []
    if not policy_context.get("household_id"):
        missing.append("household_id")
    if not policy_context.get("mandate_id"):
        missing.append("mandate_id")
    missing.extend(["account_id", "objectives", "restrictions"])
    return missing


def _client_context_reasons(policy_context: dict[str, Any]) -> list[str]:
    reasons = []
    if not policy_context.get("household_id"):
        reasons.append("CORE_HOUSEHOLD_NOT_PROVIDED")
    if not policy_context.get("mandate_id"):
        reasons.append("CORE_MANDATE_NOT_PROVIDED")
    reasons.extend(
        [
            "CORE_ACCOUNT_NOT_PROVIDED",
            "CORE_OBJECTIVES_NOT_PROVIDED",
            "CORE_RESTRICTIONS_NOT_PROVIDED",
        ]
    )
    return reasons


def _market_data_status(
    *, rows: list[Any], resolution_source: str, source_name: str
) -> ReadinessStatus:
    if not rows:
        return "BLOCKED" if source_name == "price" else "PENDING_REVIEW"
    if resolution_source != "LOTUS_CORE" or not _all_rows_open_ended(rows):
        return "PENDING_REVIEW"
    return "READY"


def _market_data_missing(*, rows: list[Any], source_name: str) -> list[str]:
    if not rows:
        return [f"{source_name} rows"]
    missing = []
    if not _all_rows_open_ended(rows):
        missing.append(f"{source_name} validity end 31-Dec-3999")
    return missing


def _market_data_reasons(*, rows: list[Any], resolution_source: str, source_name: str) -> list[str]:
    reasons = []
    if not rows:
        reasons.append(f"CORE_{source_name}_NOT_PROVIDED")
    if rows and not _all_rows_open_ended(rows):
        reasons.append(f"CORE_{source_name}_OPEN_END_DATE_NOT_PROVIDED")
    if resolution_source != "LOTUS_CORE":
        reasons.append("DIRECT_REQUEST_NOT_SOURCE_OWNER")
    return reasons


def _all_rows_open_ended(rows: list[Any]) -> bool:
    for row in rows:
        if not isinstance(row, dict):
            return False
        values = {
            str(row.get(key) or "")
            for key in (
                "valid_to",
                "validTo",
                "effective_to",
                "effectiveTo",
                "end_date",
                "endDate",
                "open_until",
                "openUntil",
            )
        }
        if not values.intersection(_OPEN_END_VALUES):
            return False
    return True


def _product_source_status(
    *, shelf_entries: list[Any], proposed_trades: list[Any]
) -> ReadinessStatus:
    if not proposed_trades:
        return "NOT_AVAILABLE"
    if not shelf_entries:
        return "BLOCKED"
    if _all_products_have_eligibility_and_complexity(shelf_entries):
        return "READY"
    return "PENDING_REVIEW"


def _product_source_missing(*, shelf_entries: list[Any], proposed_trades: list[Any]) -> list[str]:
    if not proposed_trades:
        return []
    if not shelf_entries:
        return ["shelf_entries"]
    if _all_products_have_eligibility_and_complexity(shelf_entries):
        return []
    return ["product_eligibility", "product_complexity"]


def _product_source_reasons(*, shelf_entries: list[Any], proposed_trades: list[Any]) -> list[str]:
    if not proposed_trades:
        return []
    if not shelf_entries:
        return ["CORE_PRODUCT_SHELF_NOT_PROVIDED"]
    if _all_products_have_eligibility_and_complexity(shelf_entries):
        return []
    return ["CORE_PRODUCT_ELIGIBILITY_OR_COMPLEXITY_NOT_PROVIDED"]


def _all_products_have_eligibility_and_complexity(rows: list[Any]) -> bool:
    for row in rows:
        if not isinstance(row, dict):
            return False
        raw_attributes = row.get("attributes")
        attributes: dict[str, Any] = raw_attributes if isinstance(raw_attributes, dict) else {}
        has_eligibility = bool(row.get("eligibility") or attributes.get("eligibility"))
        has_complexity = bool(
            row.get("complexity")
            or row.get("product_complexity")
            or attributes.get("complexity")
            or attributes.get("product_complexity")
        )
        if not has_eligibility or not has_complexity:
            return False
    return True


__all__ = ["build_core_memo_source_sections"]
