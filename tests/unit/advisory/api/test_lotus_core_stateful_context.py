from __future__ import annotations

from typing import Any

import pytest

from src.integrations.lotus_core.context_resolution import LotusCoreResolvedAdvisoryContext
from src.integrations.lotus_core.stateful_context import (
    LotusCoreStatefulContextUnavailableError,
    _resolve_query_base_url,
    _resolve_timeout,
    _stateful_context_cache_max_size,
    _stateful_context_cache_ttl_seconds,
    enrich_stateful_simulate_request_for_trade_drafts,
    get_stateful_context_cache_stats_for_tests,
    get_stateful_context_fetch_stats_for_tests,
    reset_stateful_context_cache_for_tests,
    resolve_stateful_context_with_lotus_core,
)
from tests.shared.stateful_context_assertions import assert_core_context_fetch_counts


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


def test_stateful_context_env_parsing_falls_back_for_invalid_values(monkeypatch) -> None:
    monkeypatch.setenv("LOTUS_CORE_TIMEOUT_SECONDS", "invalid")
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", "invalid")
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", "invalid")

    timeout = _resolve_timeout()

    assert timeout.connect == 10.0
    assert _stateful_context_cache_ttl_seconds() == 15.0
    assert _stateful_context_cache_max_size() == 128


def test_stateful_context_env_parsing_rejects_non_positive_runtime_values(monkeypatch) -> None:
    monkeypatch.setenv("LOTUS_CORE_TIMEOUT_SECONDS", "0")
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", "-1")
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", "0")

    timeout = _resolve_timeout()

    assert timeout.connect == 10.0
    assert _stateful_context_cache_ttl_seconds() == 15.0
    assert _stateful_context_cache_max_size() == 128


def test_resolve_stateful_context_with_lotus_core_builds_simulation_request(
    monkeypatch, stateful_input
):
    base_url = "http://host.docker.internal:8201"
    control_plane_base_url = "http://host.docker.internal:8202"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", control_plane_base_url)
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
                        "sector": "Information Technology",
                        "country_of_risk": "United States",
                        "product_type": "Equity",
                        "issuer_id": "ISSUER_AAPL",
                        "ultimate_parent_issuer_id": "ISSUER_AAPL",
                        "ultimate_parent_issuer_name": "Apple Inc.",
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
                        "sector": "Consumer Staples",
                        "country_of_risk": "Switzerland",
                        "product_type": "Equity",
                        "rating": "AA",
                        "issuer_id": "ISSUER_NESN",
                        "ultimate_parent_issuer_id": "ISSUER_NESN",
                        "ultimate_parent_issuer_name": "Nestle S.A.",
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
        (
            "POST",
            f"{control_plane_base_url}/integration/instruments/enrichment-bulk",
        ): _FakeResponse(
            {
                "records": [
                    {
                        "security_id": "SEC_AAPL_US",
                        "issuer_id": "ISSUER_AAPL",
                        "ultimate_parent_issuer_id": "ISSUER_AAPL",
                        "ultimate_parent_issuer_name": "Apple Inc.",
                    },
                    {
                        "security_id": "SEC_NESN_CH",
                        "issuer_id": "ISSUER_NESN",
                        "ultimate_parent_issuer_id": "ISSUER_NESN",
                        "ultimate_parent_issuer_name": "Nestle S.A.",
                    },
                ]
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
            "liquidity_tier": "L1",
            "settlement_days": 2,
            "min_notional": None,
            "attributes": {"product_type": "Cash", "source": "LOTUS_CORE_STATEFUL_CONTEXT"},
        },
        {
            "instrument_id": "SEC_AAPL_US",
            "status": "APPROVED",
            "asset_class": "EQUITY",
            "issuer_id": "ISSUER_AAPL",
            "liquidity_tier": "L1",
            "settlement_days": 2,
            "min_notional": None,
            "attributes": {
                "country": "United States",
                "product_type": "Equity",
                "sector": "Information Technology",
                "source": "LOTUS_CORE_STATEFUL_CONTEXT",
                "ultimate_parent_issuer_id": "ISSUER_AAPL",
                "ultimate_parent_issuer_name": "Apple Inc.",
            },
        },
        {
            "instrument_id": "SEC_NESN_CH",
            "status": "APPROVED",
            "asset_class": "EQUITY",
            "issuer_id": "ISSUER_NESN",
            "liquidity_tier": "L1",
            "settlement_days": 2,
            "min_notional": None,
            "attributes": {
                "country": "Switzerland",
                "product_type": "Equity",
                "rating": "AA",
                "sector": "Consumer Staples",
                "source": "LOTUS_CORE_STATEFUL_CONTEXT",
                "ultimate_parent_issuer_id": "ISSUER_NESN",
                "ultimate_parent_issuer_name": "Nestle S.A.",
            },
        },
        {
            "instrument_id": "CASH_CHF",
            "status": "APPROVED",
            "asset_class": "CASH",
            "issuer_id": None,
            "liquidity_tier": "L1",
            "settlement_days": 2,
            "min_notional": None,
            "attributes": {"product_type": "Cash", "source": "LOTUS_CORE_STATEFUL_CONTEXT"},
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
    control_plane_base_url = "http://host.docker.internal:8202"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", control_plane_base_url)
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
        (
            "POST",
            f"{control_plane_base_url}/integration/instruments/enrichment-bulk",
        ): _FakeResponse(
            {
                "records": [
                    {
                        "security_id": "SEC_AAPL_US",
                        "issuer_id": "ISSUER_AAPL",
                        "ultimate_parent_issuer_id": "ISSUER_AAPL",
                        "ultimate_parent_issuer_name": "Apple Inc.",
                    }
                ]
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
    control_plane_base_url = "http://host.docker.internal:8202"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", control_plane_base_url)
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
        (
            "POST",
            f"{control_plane_base_url}/integration/instruments/enrichment-bulk",
        ): _FakeResponse(
            {
                "records": [
                    {
                        "security_id": "SEC_AAPL_US",
                        "issuer_id": "ISSUER_AAPL",
                        "ultimate_parent_issuer_id": "ISSUER_AAPL",
                        "ultimate_parent_issuer_name": "Apple Inc.",
                    }
                ]
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
    stats = get_stateful_context_cache_stats_for_tests()
    assert stats["resolved_context"].misses == 1
    assert stats["resolved_context"].hits == 1
    assert stats["resolved_context"].writes == 1
    assert stats["resolved_context"].size == 1
    fetch_stats = get_stateful_context_fetch_stats_for_tests()
    assert_core_context_fetch_counts(fetch_stats, portfolio=1, positions=1, cash=1)


def test_resolve_stateful_context_with_lotus_core_returns_copy_safe_cached_results(
    monkeypatch, stateful_input
):
    base_url = "http://host.docker.internal:8201"
    control_plane_base_url = "http://host.docker.internal:8202"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", control_plane_base_url)
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
        (
            "POST",
            f"{control_plane_base_url}/integration/instruments/enrichment-bulk",
        ): _FakeResponse(
            {
                "records": [
                    {
                        "security_id": "SEC_AAPL_US",
                        "issuer_id": "ISSUER_AAPL",
                        "ultimate_parent_issuer_id": "ISSUER_AAPL",
                        "ultimate_parent_issuer_name": "Apple Inc.",
                    }
                ]
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


def test_resolve_stateful_context_with_lotus_core_refetches_when_cache_ttl_is_zero(
    monkeypatch, stateful_input
):
    base_url = "http://host.docker.internal:8201"
    control_plane_base_url = "http://host.docker.internal:8202"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", control_plane_base_url)
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", "0")
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

    resolve_stateful_context_with_lotus_core(stateful_input)
    resolve_stateful_context_with_lotus_core(stateful_input)

    assert request_counter["count"] == 6
    fetch_stats = get_stateful_context_fetch_stats_for_tests()
    assert_core_context_fetch_counts(fetch_stats, portfolio=2, positions=2, cash=2)


def test_resolve_stateful_context_with_lotus_core_isolates_distinct_as_of_inputs(
    monkeypatch,
):
    from src.core.workspace.models import WorkspaceStatefulInput

    base_url = "http://host.docker.internal:8201"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    request_counter = {"count": 0}
    cash_dates = iter(["2026-03-27", "2026-03-28"])

    class _AsOfAwareFakeClient(_FakeClient):
        def request(
            self,
            method: str,
            url: str,
            json: dict[str, Any] | None = None,
        ) -> _FakeResponse:
            request_counter["count"] += 1
            if method.upper() == "POST" and url == f"{base_url}/reporting/cash-balances/query":
                return _FakeResponse(
                    {
                        "portfolio_id": "DEMO_ADV_USD_001",
                        "resolved_as_of_date": next(cash_dates),
                        "cash_accounts": [],
                    }
                )
            return super().request(method, url, json=json)

    responses = {
        ("GET", f"{base_url}/portfolios/DEMO_ADV_USD_001"): _FakeResponse(
            {"portfolio_id": "DEMO_ADV_USD_001", "base_currency": "USD"}
        ),
        ("GET", f"{base_url}/portfolios/DEMO_ADV_USD_001/positions"): _FakeResponse(
            {"portfolio_id": "DEMO_ADV_USD_001", "positions": []}
        ),
    }
    monkeypatch.setattr(
        "src.integrations.lotus_core.stateful_context.httpx.Client",
        lambda timeout: _AsOfAwareFakeClient(responses),
    )

    first = resolve_stateful_context_with_lotus_core(
        WorkspaceStatefulInput(portfolio_id="DEMO_ADV_USD_001", as_of="2026-03-27")
    )
    second = resolve_stateful_context_with_lotus_core(
        WorkspaceStatefulInput(portfolio_id="DEMO_ADV_USD_001", as_of="2026-03-28")
    )

    assert first.resolved_context.as_of == "2026-03-27"
    assert second.resolved_context.as_of == "2026-03-28"
    assert (
        first.resolved_context.portfolio_snapshot_id
        != second.resolved_context.portfolio_snapshot_id
    )
    assert request_counter["count"] == 6
    fetch_stats = get_stateful_context_fetch_stats_for_tests()
    assert_core_context_fetch_counts(fetch_stats, portfolio=2, positions=2, cash=2)


def test_resolve_stateful_context_with_lotus_core_isolates_optional_identity_dimensions(
    monkeypatch,
):
    from src.core.workspace.models import WorkspaceStatefulInput

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

    first = resolve_stateful_context_with_lotus_core(
        WorkspaceStatefulInput(
            portfolio_id="DEMO_ADV_USD_001",
            as_of="2026-03-27",
            mandate_id="mandate_growth_01",
            benchmark_id="benchmark_balanced_usd",
        )
    )
    second = resolve_stateful_context_with_lotus_core(
        WorkspaceStatefulInput(
            portfolio_id="DEMO_ADV_USD_001",
            as_of="2026-03-27",
            mandate_id="mandate_income_01",
            benchmark_id="benchmark_income_usd",
        )
    )

    assert first.resolved_context == second.resolved_context
    assert request_counter["count"] == 6
    stats = get_stateful_context_cache_stats_for_tests()
    assert stats["resolved_context"].misses == 2
    assert stats["resolved_context"].hits == 0
    assert stats["resolved_context"].writes == 2
    fetch_stats = get_stateful_context_fetch_stats_for_tests()
    assert_core_context_fetch_counts(fetch_stats, portfolio=2, positions=2, cash=2)


def test_resolve_stateful_context_with_lotus_core_evicts_oldest_cache_entry(
    monkeypatch,
):
    from src.core.workspace.models import WorkspaceStatefulInput

    base_url = "http://host.docker.internal:8201"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", "1")
    request_counter = {"count": 0}
    responses = {
        ("GET", f"{base_url}/portfolios/pf_cache_a"): _FakeResponse(
            {"portfolio_id": "pf_cache_a", "base_currency": "USD"}
        ),
        ("GET", f"{base_url}/portfolios/pf_cache_a/positions"): _FakeResponse(
            {"portfolio_id": "pf_cache_a", "positions": []}
        ),
        ("GET", f"{base_url}/portfolios/pf_cache_b"): _FakeResponse(
            {"portfolio_id": "pf_cache_b", "base_currency": "USD"}
        ),
        ("GET", f"{base_url}/portfolios/pf_cache_b/positions"): _FakeResponse(
            {"portfolio_id": "pf_cache_b", "positions": []}
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
            if method.upper() == "POST" and url == f"{base_url}/reporting/cash-balances/query":
                portfolio_id = (json or {}).get("portfolio_id")
                if portfolio_id == "pf_cache_a":
                    return _FakeResponse(
                        {
                            "portfolio_id": "pf_cache_a",
                            "resolved_as_of_date": "2026-03-27",
                            "cash_accounts": [],
                        }
                    )
                if portfolio_id == "pf_cache_b":
                    return _FakeResponse(
                        {
                            "portfolio_id": "pf_cache_b",
                            "resolved_as_of_date": "2026-03-27",
                            "cash_accounts": [],
                        }
                    )
            return super().request(method, url, json=json)

    monkeypatch.setattr(
        "src.integrations.lotus_core.stateful_context.httpx.Client",
        lambda timeout: _CountingFakeClient(responses),
    )

    first = WorkspaceStatefulInput(portfolio_id="pf_cache_a", as_of="2026-03-27")
    second = WorkspaceStatefulInput(portfolio_id="pf_cache_b", as_of="2026-03-27")

    resolve_stateful_context_with_lotus_core(first)
    resolve_stateful_context_with_lotus_core(second)
    resolve_stateful_context_with_lotus_core(first)

    assert request_counter["count"] == 9


def test_resolve_stateful_context_with_lotus_core_does_not_cache_failures(
    monkeypatch, stateful_input
):
    base_url = "http://host.docker.internal:8201"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    request_counter = {"count": 0}
    responses = {
        ("GET", f"{base_url}/portfolios/DEMO_ADV_USD_001"): _FakeResponse(
            {"portfolio_id": "DEMO_ADV_USD_001", "base_currency": ""}
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

    with pytest.raises(LotusCoreStatefulContextUnavailableError):
        resolve_stateful_context_with_lotus_core(stateful_input)
    with pytest.raises(LotusCoreStatefulContextUnavailableError):
        resolve_stateful_context_with_lotus_core(stateful_input)

    assert request_counter["count"] == 6


def test_resolve_stateful_context_with_lotus_core_recovers_after_failed_resolution(
    monkeypatch, stateful_input
):
    base_url = "http://host.docker.internal:8201"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    request_counter = {"count": 0}
    portfolio_payload = {"portfolio_id": "DEMO_ADV_USD_001", "base_currency": ""}

    class _RecoveringFakeClient:
        def __enter__(self) -> "_RecoveringFakeClient":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def request(
            self,
            method: str,
            url: str,
            json: dict[str, Any] | None = None,
        ) -> _FakeResponse:
            request_counter["count"] += 1
            if (method.upper(), url) == ("GET", f"{base_url}/portfolios/DEMO_ADV_USD_001"):
                return _FakeResponse(dict(portfolio_payload))
            if (method.upper(), url) == (
                "GET",
                f"{base_url}/portfolios/DEMO_ADV_USD_001/positions",
            ):
                return _FakeResponse({"portfolio_id": "DEMO_ADV_USD_001", "positions": []})
            if (method.upper(), url) == ("POST", f"{base_url}/reporting/cash-balances/query"):
                return _FakeResponse(
                    {
                        "portfolio_id": "DEMO_ADV_USD_001",
                        "resolved_as_of_date": "2026-03-27",
                        "cash_accounts": [],
                    }
                )
            raise AssertionError(f"unexpected request: {(method.upper(), url)} body={json}")

    monkeypatch.setattr(
        "src.integrations.lotus_core.stateful_context.httpx.Client",
        lambda timeout: _RecoveringFakeClient(),
    )

    with pytest.raises(LotusCoreStatefulContextUnavailableError):
        resolve_stateful_context_with_lotus_core(stateful_input)

    portfolio_payload["base_currency"] = "USD"
    recovered = resolve_stateful_context_with_lotus_core(stateful_input)

    assert recovered.resolved_context.portfolio_id == "DEMO_ADV_USD_001"
    assert request_counter["count"] == 6
    stats = get_stateful_context_cache_stats_for_tests()
    assert stats["resolved_context"].misses == 2
    assert stats["resolved_context"].expirations == 0
    assert stats["resolved_context"].writes == 1
    fetch_stats = get_stateful_context_fetch_stats_for_tests()
    assert_core_context_fetch_counts(fetch_stats, portfolio=2, positions=2, cash=2)


def test_enrich_stateful_simulate_request_for_trade_drafts_adds_missing_trade_inputs(
    monkeypatch,
):
    from src.core.models import ProposalSimulateRequest

    base_url = "http://host.docker.internal:8201"
    control_plane_base_url = "http://host.docker.internal:8202"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", control_plane_base_url)
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
        (
            "POST",
            f"{control_plane_base_url}/integration/instruments/enrichment-bulk",
        ): _FakeResponse(
            {
                "records": [
                    {
                        "security_id": "EQ_NEW_CHF",
                        "issuer_id": "ISSUER_EQ_NEW_CHF",
                        "ultimate_parent_issuer_id": "ULTIMATE_EQ_NEW_CHF",
                        "ultimate_parent_issuer_name": "Issuer Parent AG",
                    }
                ]
            }
        ),
        ("GET", f"{base_url}/instruments/?security_id=EQ_NEW_CHF"): _FakeResponse(
            {
                "total": 1,
                "instruments": [
                    {
                        "security_id": "EQ_NEW_CHF",
                        "currency": "CHF",
                        "asset_class": "Equity",
                        "sector": "Industrials",
                        "country_of_risk": "Switzerland",
                        "product_type": "Equity",
                        "rating": "A",
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
    assert enriched.shelf_entries[-1].model_dump(mode="json")["issuer_id"] == "ISSUER_EQ_NEW_CHF"
    assert enriched.shelf_entries[-1].model_dump(mode="json")["liquidity_tier"] == "L1"
    assert enriched.shelf_entries[-1].model_dump(mode="json")["attributes"] == {
        "country": "Switzerland",
        "product_type": "Equity",
        "rating": "A",
        "sector": "Industrials",
        "source": "LOTUS_CORE_STATEFUL_CONTEXT",
        "ultimate_parent_issuer_id": "ULTIMATE_EQ_NEW_CHF",
        "ultimate_parent_issuer_name": "Issuer Parent AG",
    }
    assert enriched.market_data_snapshot.model_dump(mode="json")["fx_rates"][-1] == {
        "pair": "CHF/USD",
        "rate": "1.10",
    }
    fetch_stats = get_stateful_context_fetch_stats_for_tests()
    assert fetch_stats.instrument_fetches == 2
    assert fetch_stats.price_fetches == 1
    assert fetch_stats.fx_fetches == 1


def test_enrich_stateful_simulate_request_for_trade_drafts_reuses_lookup_cache_stats(
    monkeypatch,
):
    from src.core.models import ProposalSimulateRequest

    base_url = "http://host.docker.internal:8201"
    control_plane_base_url = "http://host.docker.internal:8202"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", control_plane_base_url)
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
                    "instrument_id": "EQ_NEW_CHF",
                    "quantity": "4",
                }
            ],
        }
    )
    request_counter = {"count": 0}
    responses = {
        (
            "POST",
            f"{control_plane_base_url}/integration/instruments/enrichment-bulk",
        ): _FakeResponse(
            {
                "records": [
                    {
                        "security_id": "EQ_NEW_CHF",
                        "issuer_id": "ISSUER_EQ_NEW_CHF",
                        "ultimate_parent_issuer_id": "ULTIMATE_EQ_NEW_CHF",
                        "ultimate_parent_issuer_name": "Issuer Parent AG",
                    }
                ]
            }
        ),
        ("GET", f"{base_url}/instruments/?security_id=EQ_NEW_CHF"): _FakeResponse(
            {
                "total": 1,
                "instruments": [
                    {
                        "security_id": "EQ_NEW_CHF",
                        "currency": "CHF",
                        "asset_class": "Equity",
                        "sector": "Industrials",
                        "country_of_risk": "Switzerland",
                        "product_type": "Equity",
                        "rating": "A",
                    }
                ],
            }
        ),
        ("GET", f"{base_url}/prices/?security_id=EQ_NEW_CHF"): _FakeResponse(
            {
                "security_id": "EQ_NEW_CHF",
                "prices": [{"price_date": "2026-03-25", "price": "50.0", "currency": "CHF"}],
            }
        ),
        ("GET", f"{base_url}/fx-rates/?from_currency=CHF&to_currency=USD"): _FakeResponse(
            {
                "from_currency": "CHF",
                "to_currency": "USD",
                "rates": [{"rate_date": "2026-03-25", "rate": "1.10"}],
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

    enrich_stateful_simulate_request_for_trade_drafts(
        simulate_request=simulate_request,
        as_of="2026-03-25",
    )
    enrich_stateful_simulate_request_for_trade_drafts(
        simulate_request=simulate_request,
        as_of="2026-03-25",
    )

    assert request_counter["count"] == 4
    stats = get_stateful_context_cache_stats_for_tests()
    assert stats["instrument_lookup"].misses == 1
    assert stats["instrument_lookup"].hits == 1
    assert stats["price_lookup"].misses == 1
    assert stats["price_lookup"].hits == 1
    assert stats["fx_lookup"].misses == 1
    assert stats["fx_lookup"].hits == 1
    fetch_stats = get_stateful_context_fetch_stats_for_tests()
    assert fetch_stats.instrument_fetches == 2
    assert fetch_stats.price_fetches == 1
    assert fetch_stats.fx_fetches == 1


def test_enrich_stateful_simulate_request_for_trade_drafts_skips_malformed_lookup_rows(
    monkeypatch,
):
    from src.core.models import ProposalSimulateRequest

    base_url = "http://host.docker.internal:8201"
    control_plane_base_url = "http://host.docker.internal:8202"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", control_plane_base_url)
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
        (
            "POST",
            f"{control_plane_base_url}/integration/instruments/enrichment-bulk",
        ): _FakeResponse(
            {"records": [{"security_id": "EQ_BAD", "issuer_id": "ISSUER_BAD"}]}
        ),
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
