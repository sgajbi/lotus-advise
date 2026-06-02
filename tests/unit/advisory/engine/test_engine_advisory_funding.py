from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from src.core.advisory.funding import funding_priority_currencies
from src.core.advisory.funding_selection import select_funding_source
from src.core.portfolio_models import MarketDataSnapshot, PortfolioSnapshot

REPO_ROOT = Path(__file__).resolve().parents[4]


class _Options:
    def __init__(self, fx_funding_source_currency: str):
        self.fx_funding_source_currency = fx_funding_source_currency


def test_funding_priority_base_only_prefers_base_when_different_target_currency():
    result = funding_priority_currencies(
        options=_Options("BASE_ONLY"),
        base_currency="USD",
        target_currency="EUR",
        cash_ledger={"USD": 1000, "EUR": 0, "SGD": 10},
    )
    assert result == ["USD"]


def test_select_funding_source_prefers_first_sufficient_base_cash():
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_funding_select",
        base_currency="SGD",
        positions=[],
        cash_balances=[
            {"currency": "SGD", "amount": "2000"},
            {"currency": "USD", "amount": "0"},
        ],
    )
    market_data = MarketDataSnapshot(
        prices=[],
        fx_rates=[{"pair": "USD/SGD", "rate": "1.35"}],
    )
    diagnostics = SimpleNamespace(missing_fx_pairs=[], data_quality={"fx_missing": []})

    selected, deficit = select_funding_source(
        after_portfolio=portfolio,
        market_data=market_data,
        options=_Options("BASE_ONLY"),
        diagnostics=diagnostics,
        target_currency="USD",
        fx_needed=Decimal("1000"),
        cash_ledger={"SGD": Decimal("2000"), "USD": Decimal("0")},
    )

    assert selected is not None
    assert selected["pair"] == "USD/SGD"
    assert selected["funding_currency"] == "SGD"
    assert selected["sell_required"] == Decimal("1350.00")
    assert deficit is None
    assert diagnostics.missing_fx_pairs == []


def test_select_funding_source_records_missing_fx_pair():
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_funding_missing_fx",
        base_currency="SGD",
        positions=[],
        cash_balances=[{"currency": "SGD", "amount": "2000"}],
    )
    market_data = MarketDataSnapshot(prices=[], fx_rates=[])
    diagnostics = SimpleNamespace(missing_fx_pairs=[], data_quality={"fx_missing": []})

    selected, deficit = select_funding_source(
        after_portfolio=portfolio,
        market_data=market_data,
        options=_Options("BASE_ONLY"),
        diagnostics=diagnostics,
        target_currency="USD",
        fx_needed=Decimal("1000"),
        cash_ledger={"SGD": Decimal("2000")},
    )

    assert selected is None
    assert deficit is None
    assert diagnostics.missing_fx_pairs == ["USD/SGD"]
    assert diagnostics.data_quality["fx_missing"] == ["USD/SGD"]


def test_auto_funding_plan_delegates_source_selection():
    source = (REPO_ROOT / "src/core/advisory/funding.py").read_text(encoding="utf-8")

    assert "from src.core.advisory.funding_selection import" in source
    assert "select_funding_source(" in source
    assert "get_fx_rate(" not in source
