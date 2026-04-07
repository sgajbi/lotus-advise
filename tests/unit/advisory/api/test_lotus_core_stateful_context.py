from __future__ import annotations

from typing import Any

import pytest

from src.integrations.lotus_core.context_resolution import LotusCoreResolvedAdvisoryContext
from src.integrations.lotus_core.stateful_context import (
    LotusCoreStatefulContextUnavailableError,
    _resolve_query_base_url,
    enrich_stateful_simulate_request_for_trade_drafts,
    reset_stateful_context_cache_for_tests,
    resolve_stateful_context_with_lotus_core,
)


class _FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("boom")

    def json(self) -> Any:
        return self._payload


class _FakeClient:
    def __init__(self, responses: dict[tuple[str, str], _FakeResponse]) -> None:
        self._responses = responses

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def request(self, method: str, url: str, json: dict[str, Any] | None = None) -> _FakeResponse:
        key = (method.upper(), url)
        if key not in self._responses:
            raise AssertionError(f"unexpected request: {key} body={json}")
        return self._responses[key]


@pytest.fixture
def stateful_input():
    from src.core.workspace.models import WorkspaceStatefulInput

    return WorkspaceStatefulInput(
        portfolio_id="DEMO_ADV_USD_001",
        as_of="2026-03-27",
        mandate_id="mandate_growth_01",
    )


@pytest.fixture(autouse=True)
def reset_stateful_context_cache():
    reset_stateful_context_cache_for_tests()
    yield
    reset_stateful_context_cache_for_tests()


def test_query_base_url_derives_query_service_from_control_plane_env(monkeypatch):
    monkeypatch.delenv("LOTUS_CORE_QUERY_BASE_URL", raising=False)
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://host.docker.internal:8202")

    assert _resolve_query_base_url() == "http://host.docker.internal:8201"


def test_query_base_url_prefers_explicit_query_env(monkeypatch):
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://host.docker.internal:8202")
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", "http://query.example.internal:9999/")

    assert _resolve_query_base_url() == "http://query.example.internal:9999"


def test_resolve_stateful_context_with_lotus_core_builds_simulation_request(
    monkeypatch, stateful_input
):
    base_url = "http://host.docker.internal:8201"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    responses = {
        (
            "GET",
            f"{base_url}/portfolios/DEMO_ADV_USD_001",
        ): _FakeResponse(
            {
                "portfolio_id": "DEMO_ADV_USD_001",
                "base_currency": "USD",
            }
        ),
        (
            "GET",
            f"{base_url}/portfolios/DEMO_ADV_USD_001/positions",
        ): _FakeResponse(
            {
                "portfolio_id": "DEMO_ADV_USD_001",
                "positions": [
                    {
                        "security_id": "CASH_USD",
                        "quantity": 235350.0,
                        "asset_class": "Cash",
                        "currency": "USD",
                        "valuation": {
                            "market_price": "1.0000000000",
                            "market_value": "235350.0000000000",
                            "market_value_local": "235350.0000000000",
                        },
                    },
                    {
                        "security_id": "SEC_AAPL_US",
                        "quantity": 800.0,
                        "asset_class": "Equity",
                        "currency": "USD",
                        "valuation": {
                            "market_price": "194.0000000000",
                            "market_value": "155200.0000000000",
                            "market_value_local": "155200.0000000000",
                        },
                    },
                    {
                        "security_id": "SEC_NESN_CH",
                        "quantity": 120.0,
                        "asset_class": "Equity",
                        "currency": "CHF",
                        "valuation": {
                            "market_price": "94.5000000000",
                            "market_value": "12400.0000000000",
                            "market_value_local": "11340.0000000000",
                        },
                    },
                ],
            }
        ),
        (
            "POST",
            f"{base_url}/reporting/cash-balances/query",
        ): _FakeResponse(
            {
                "portfolio_id": "DEMO_ADV_USD_001",
                "portfolio_currency": "USD",
                "resolved_as_of_date": "2026-03-27",
                "cash_accounts": [
                    {
                        "cash_account_id": "CASH_USD",
                        "instrument_id": "CASH_USD",
                        "security_id": "CASH_USD",
                        "account_currency": "USD",
                        "balance_account_currency": "235350.0000000000",
                        "balance_portfolio_currency": "235350.0000000000",
                    },
                    {
                        "cash_account_id": "CASH_CHF",
                        "instrument_id": "CASH_CHF",
                        "security_id": "CASH_CHF",
                        "account_currency": "CHF",
                        "balance_account_currency": "1000.0000000000",
                        "balance_portfolio_currency": "1093.0000000000",
                    },
                ],
            }
        ),
    }
    monkeypatch.setattr(
        "src.integrations.lotus_core.stateful_context.httpx.Client",
        lambda timeout: _FakeClient(responses),
    )

    resolved = resolve_stateful_context_with_lotus_core(stateful_input)

    assert isinstance(resolved, LotusCoreResolvedAdvisoryContext)
    assert resolved.resolved_context.portfolio_id == "DEMO_ADV_USD_001"
    assert resolved.resolved_context.as_of == "2026-03-27"
    assert resolved.resolved_context.portfolio_snapshot_id == (
        "lotus-core:portfolio:DEMO_ADV_USD_001:2026-03-27"
    )
    request = resolved.simulate_request
    assert request.portfolio_snapshot.base_currency == "USD"
    assert request.portfolio_snapshot.model_dump(mode="json")["positions"] == [
        {"instrument_id": "SEC_AAPL_US", "quantity": "800.0", "market_value": None, "lots": []},
        {"instrument_id": "SEC_NESN_CH", "quantity": "120.0", "market_value": None, "lots": []},
    ]
    assert request.portfolio_snapshot.model_dump(mode="json")["cash_balances"] == [
        {"currency": "USD", "amount": "235350.0000000000", "settled": None, "pending": None},
        {"currency": "CHF", "amount": "1000.0000000000", "settled": None, "pending": None},
    ]
    assert request.market_data_snapshot.model_dump(mode="json")["prices"] == [
        {"instrument_id": "SEC_AAPL_US", "price": "194.0000000000", "currency": "USD"},
        {"instrument_id": "SEC_NESN_CH", "price": "94.5000000000", "currency": "CHF"},
    ]
    assert [entry.model_dump(mode="json") for entry in request.shelf_entries] == [
        {
            "instrument_id": "CASH_USD",
            "status": "APPROVED",
            "asset_class": "CASH",
            "issuer_id": None,
            "liquidity_tier": None,
            "settlement_days": 2,
            "min_notional": None,
            "attributes": {"source": "LOTUS_CORE_STATEFUL_CONTEXT"},
        },
        {
            "instrument_id": "SEC_AAPL_US",
            "status": "APPROVED",
            "asset_class": "EQUITY",
            "issuer_id": None,
            "liquidity_tier": None,
            "settlement_days": 2,
            "min_notional": None,
            "attributes": {"source": "LOTUS_CORE_STATEFUL_CONTEXT"},
        },
        {
            "instrument_id": "SEC_NESN_CH",
            "status": "APPROVED",
            "asset_class": "EQUITY",
            "issuer_id": None,
            "liquidity_tier": None,
            "settlement_days": 2,
            "min_notional": None,
            "attributes": {"source": "LOTUS_CORE_STATEFUL_CONTEXT"},
        },
        {
            "instrument_id": "CASH_CHF",
            "status": "APPROVED",
            "asset_class": "CASH",
            "issuer_id": None,
            "liquidity_tier": None,
            "settlement_days": 2,
            "min_notional": None,
            "attributes": {"source": "LOTUS_CORE_STATEFUL_CONTEXT"},
        },
    ]
    assert request.market_data_snapshot.model_dump(mode="json")["fx_rates"] == [
        {"pair": "CHF/USD", "rate": "1.093"},
    ]
    assert request.options.enable_proposal_simulation is True
    assert request.proposed_cash_flows == []
    assert request.proposed_trades == []


def test_resolve_stateful_context_with_lotus_core_rejects_invalid_portfolio_payload(
    monkeypatch, stateful_input
):
    base_url = "http://host.docker.internal:8201"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    responses = {
        ("GET", f"{base_url}/portfolios/DEMO_ADV_USD_001"): _FakeResponse({"portfolio_id": ""}),
        ("GET", f"{base_url}/portfolios/DEMO_ADV_USD_001/positions"): _FakeResponse(
            {"portfolio_id": "DEMO_ADV_USD_001", "positions": []}
        ),
        ("POST", f"{base_url}/reporting/cash-balances/query"): _FakeResponse(
            {
                "portfolio_id": "DEMO_ADV_USD_001",
                "resolved_as_of_date": "2026-03-27",
                "cash_accounts": [],
            }
        ),
    }
    monkeypatch.setattr(
        "src.integrations.lotus_core.stateful_context.httpx.Client",
        lambda timeout: _FakeClient(responses),
    )

    with pytest.raises(LotusCoreStatefulContextUnavailableError) as exc_info:
        resolve_stateful_context_with_lotus_core(stateful_input)

    assert str(exc_info.value) == "LOTUS_CORE_STATEFUL_CONTEXT_INVALID"


def test_resolve_stateful_context_with_lotus_core_reuses_cached_context(
    monkeypatch, stateful_input
):
    base_url = "http://host.docker.internal:8201"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    request_counter = {"count": 0}
    responses = {
        ("GET", f"{base_url}/portfolios/DEMO_ADV_USD_001"): _FakeResponse(
            {"portfolio_id": "DEMO_ADV_USD_001", "base_currency": "USD"}
        ),
        ("GET", f"{base_url}/portfolios/DEMO_ADV_USD_001/positions"): _FakeResponse(
            {"portfolio_id": "DEMO_ADV_USD_001", "positions": []}
        ),
        ("POST", f"{base_url}/reporting/cash-balances/query"): _FakeResponse(
            {
                "portfolio_id": "DEMO_ADV_USD_001",
                "resolved_as_of_date": "2026-03-27",
                "cash_accounts": [],
            }
        ),
    }

    class _CountingFakeClient(_FakeClient):
        def request(
            self,
            method: str,
            url: str,
            json: dict[str, Any] | None = None,
        ) -> _FakeResponse:
            request_counter["count"] += 1
            return super().request(method, url, json=json)

    monkeypatch.setattr(
        "src.integrations.lotus_core.stateful_context.httpx.Client",
        lambda timeout: _CountingFakeClient(responses),
    )

    first = resolve_stateful_context_with_lotus_core(stateful_input)
    second = resolve_stateful_context_with_lotus_core(stateful_input)

    assert first.resolved_context == second.resolved_context
    assert request_counter["count"] == 3


def test_resolve_stateful_context_with_lotus_core_returns_copy_safe_cached_results(
    monkeypatch, stateful_input
):
    base_url = "http://host.docker.internal:8201"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    responses = {
        ("GET", f"{base_url}/portfolios/DEMO_ADV_USD_001"): _FakeResponse(
            {"portfolio_id": "DEMO_ADV_USD_001", "base_currency": "USD"}
        ),
        ("GET", f"{base_url}/portfolios/DEMO_ADV_USD_001/positions"): _FakeResponse(
            {
                "portfolio_id": "DEMO_ADV_USD_001",
                "positions": [
                    {
                        "security_id": "SEC_AAPL_US",
                        "quantity": 800.0,
                        "asset_class": "Equity",
                        "currency": "USD",
                        "valuation": {
                            "market_price": "194.0000000000",
                            "market_value": "155200.0000000000",
                            "market_value_local": "155200.0000000000",
                        },
                    }
                ],
            }
        ),
        ("POST", f"{base_url}/reporting/cash-balances/query"): _FakeResponse(
            {
                "portfolio_id": "DEMO_ADV_USD_001",
                "resolved_as_of_date": "2026-03-27",
                "cash_accounts": [],
            }
        ),
    }
    monkeypatch.setattr(
        "src.integrations.lotus_core.stateful_context.httpx.Client",
        lambda timeout: _FakeClient(responses),
    )

    first = resolve_stateful_context_with_lotus_core(stateful_input)
    first.simulate_request.portfolio_snapshot.positions[0].instrument_id = "MUTATED"

    second = resolve_stateful_context_with_lotus_core(stateful_input)

    assert second.simulate_request.portfolio_snapshot.positions[0].instrument_id == "SEC_AAPL_US"


def test_enrich_stateful_simulate_request_for_trade_drafts_adds_missing_trade_inputs(
    monkeypatch,
):
    from src.core.models import ProposalSimulateRequest

    base_url = "http://host.docker.internal:8201"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    simulate_request = ProposalSimulateRequest.model_validate(
        {
            "portfolio_snapshot": {
                "snapshot_id": "ps_001",
                "portfolio_id": "pf_001",
                "base_currency": "USD",
                "positions": [{"instrument_id": "EQ_OLD", "quantity": "10"}],
                "cash_balances": [{"currency": "USD", "amount": "10000"}],
            },
            "market_data_snapshot": {
                "snapshot_id": "md_001",
                "prices": [{"instrument_id": "EQ_OLD", "price": "100", "currency": "USD"}],
                "fx_rates": [],
            },
            "shelf_entries": [{"instrument_id": "EQ_OLD", "status": "APPROVED"}],
            "options": {"enable_proposal_simulation": True},
            "proposed_cash_flows": [],
            "proposed_trades": [
                {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": "EQ_NEW_CHF",
                    "quantity": "4",
                }
            ],
        }
    )
    responses = {
        ("GET", f"{base_url}/instruments/?security_id=EQ_NEW_CHF"): _FakeResponse(
            {
                "total": 1,
                "instruments": [
                    {
                        "security_id": "EQ_NEW_CHF",
                        "currency": "CHF",
                        "asset_class": "Equity",
                    }
                ],
            }
        ),
        ("GET", f"{base_url}/prices/?security_id=EQ_NEW_CHF"): _FakeResponse(
            {
                "security_id": "EQ_NEW_CHF",
                "prices": [
                    {"price_date": "2026-03-24", "price": "49.5", "currency": "CHF"},
                    {"price_date": "2026-03-25", "price": "50.0", "currency": "CHF"},
                ],
            }
        ),
        ("GET", f"{base_url}/fx-rates/?from_currency=CHF&to_currency=USD"): _FakeResponse(
            {
                "from_currency": "CHF",
                "to_currency": "USD",
                "rates": [
                    {"rate_date": "2026-03-25", "rate": "1.10"},
                ],
            }
        ),
    }
    monkeypatch.setattr(
        "src.integrations.lotus_core.stateful_context.httpx.Client",
        lambda timeout: _FakeClient(responses),
    )

    enriched = enrich_stateful_simulate_request_for_trade_drafts(
        simulate_request=simulate_request,
        as_of="2026-03-25",
    )

    assert simulate_request.market_data_snapshot.model_dump(mode="json")["prices"] == [
        {"instrument_id": "EQ_OLD", "price": "100", "currency": "USD"}
    ]
    assert enriched.market_data_snapshot.model_dump(mode="json")["prices"][-1] == {
        "instrument_id": "EQ_NEW_CHF",
        "price": "50.0",
        "currency": "CHF",
    }
    assert enriched.shelf_entries[-1].model_dump(mode="json")["instrument_id"] == "EQ_NEW_CHF"
    assert enriched.market_data_snapshot.model_dump(mode="json")["fx_rates"][-1] == {
        "pair": "CHF/USD",
        "rate": "1.10",
    }


def test_enrich_stateful_simulate_request_for_trade_drafts_skips_malformed_lookup_rows(
    monkeypatch,
):
    from src.core.models import ProposalSimulateRequest

    base_url = "http://host.docker.internal:8201"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    simulate_request = ProposalSimulateRequest.model_validate(
        {
            "portfolio_snapshot": {
                "snapshot_id": "ps_001",
                "portfolio_id": "pf_001",
                "base_currency": "USD",
                "positions": [],
                "cash_balances": [{"currency": "USD", "amount": "10000"}],
            },
            "market_data_snapshot": {"snapshot_id": "md_001", "prices": [], "fx_rates": []},
            "shelf_entries": [],
            "options": {"enable_proposal_simulation": True},
            "proposed_cash_flows": [],
            "proposed_trades": [
                {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": "EQ_BAD",
                    "quantity": "2",
                }
            ],
        }
    )
    responses = {
        ("GET", f"{base_url}/instruments/?security_id=EQ_BAD"): _FakeResponse(
            {"total": 1, "instruments": ["not-a-dict"]}
        ),
    }
    monkeypatch.setattr(
        "src.integrations.lotus_core.stateful_context.httpx.Client",
        lambda timeout: _FakeClient(responses),
    )

    enriched = enrich_stateful_simulate_request_for_trade_drafts(
        simulate_request=simulate_request,
        as_of="2026-03-25",
    )

    assert enriched.model_dump(mode="json") == simulate_request.model_dump(mode="json")


def test_enrich_stateful_simulate_request_for_trade_drafts_avoids_duplicate_entries(
    monkeypatch,
):
    from src.core.models import ProposalSimulateRequest

    base_url = "http://host.docker.internal:8201"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    simulate_request = ProposalSimulateRequest.model_validate(
        {
            "portfolio_snapshot": {
                "snapshot_id": "ps_001",
                "portfolio_id": "pf_001",
                "base_currency": "USD",
                "positions": [],
                "cash_balances": [{"currency": "USD", "amount": "10000"}],
            },
            "market_data_snapshot": {
                "snapshot_id": "md_001",
                "prices": [{"instrument_id": "EQ_NEW_CHF", "price": "50", "currency": "CHF"}],
                "fx_rates": [{"pair": "CHF/USD", "rate": "1.10"}],
            },
            "shelf_entries": [{"instrument_id": "EQ_NEW_CHF", "status": "APPROVED"}],
            "options": {"enable_proposal_simulation": True},
            "proposed_cash_flows": [],
            "proposed_trades": [
                {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": "EQ_NEW_CHF",
                    "quantity": "4",
                }
            ],
        }
    )

    enriched = enrich_stateful_simulate_request_for_trade_drafts(
        simulate_request=simulate_request,
        as_of="2026-03-25",
    )

    assert len(enriched.market_data_snapshot.prices) == 1
    assert len(enriched.market_data_snapshot.fx_rates) == 1
    assert len(enriched.shelf_entries) == 1
