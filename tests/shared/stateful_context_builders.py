from __future__ import annotations

from typing import Any


def build_resolved_stateful_context(
    portfolio_id: str,
    as_of: str,
    *,
    positions: list[dict[str, Any]] | None = None,
    cash_amount: str = "1000",
    prices: list[dict[str, Any]] | None = None,
    shelf_entries: list[dict[str, Any]] | None = None,
    options: dict[str, Any] | None = None,
    include_context_ids: bool = True,
) -> dict[str, Any]:
    resolved_context: dict[str, Any] = {
        "portfolio_id": portfolio_id,
        "as_of": as_of,
        "portfolio_snapshot_id": f"ps_{portfolio_id}_{as_of}",
        "market_data_snapshot_id": f"md_{as_of}",
    }
    if include_context_ids:
        resolved_context["risk_context_id"] = "risk_ctx_001"
        resolved_context["reporting_context_id"] = "report_ctx_001"

    return {
        "simulate_request": {
            "portfolio_snapshot": {
                "snapshot_id": f"ps_{portfolio_id}_{as_of}",
                "portfolio_id": portfolio_id,
                "base_currency": "USD",
                "positions": positions or [],
                "cash_balances": [{"currency": "USD", "amount": cash_amount}],
            },
            "market_data_snapshot": {
                "snapshot_id": f"md_{as_of}",
                "prices": prices or [],
                "fx_rates": [],
            },
            "shelf_entries": shelf_entries or [],
            "options": options or {"enable_proposal_simulation": True},
            "proposed_cash_flows": [],
            "proposed_trades": [],
        },
        "resolved_context": resolved_context,
    }


def build_tradeable_universe_stateful_context(
    portfolio_id: str,
    as_of: str,
) -> dict[str, Any]:
    return build_resolved_stateful_context(
        portfolio_id,
        as_of,
        positions=[{"instrument_id": "EQ_OLD", "quantity": "10"}],
        cash_amount="10000",
        prices=[
            {"instrument_id": "EQ_OLD", "price": "100", "currency": "USD"},
            {"instrument_id": "EQ_NEW", "price": "50", "currency": "USD"},
        ],
        shelf_entries=[
            {"instrument_id": "EQ_OLD", "status": "APPROVED"},
            {"instrument_id": "EQ_NEW", "status": "APPROVED"},
        ],
        options={
            "enable_proposal_simulation": True,
            "enable_workflow_gates": True,
            "enable_suitability_scanner": True,
        },
        include_context_ids=False,
    )
