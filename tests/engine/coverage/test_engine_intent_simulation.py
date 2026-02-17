from decimal import Decimal

from src.core.engine import _generate_fx_and_simulate, run_simulation
from src.core.models import (
    CashBalance,
    EngineOptions,
    FxRate,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    PortfolioSnapshot,
    Position,
    Price,
    SecurityTradeIntent,
    ShelfEntry,
)
from tests.engine.coverage.helpers import empty_diagnostics, usd_cash_portfolio


class TestIntentDependenciesAndSimulation:
    def test_dependency_linking_explicit(self):
        pf = usd_cash_portfolio("dep_test")
        mkt = MarketDataSnapshot(
            prices=[Price(instrument_id="GBP_STK", price=Decimal("100"), currency="GBP")],
            fx_rates=[FxRate(pair="GBP/USD", rate=Decimal("1.2"))],
        )
        shelf = [ShelfEntry(instrument_id="GBP_STK", status="APPROVED")]
        model = ModelPortfolio(
            targets=[ModelTarget(instrument_id="GBP_STK", weight=Decimal("1.0"))]
        )

        result = run_simulation(pf, mkt, model, shelf, EngineOptions())

        buy = next(
            i for i in result.intents if isinstance(i, SecurityTradeIntent) and i.side == "BUY"
        )
        assert len(buy.dependencies) > 0

    def test_dependency_sell_linking(self):
        pf = PortfolioSnapshot(
            portfolio_id="p_chain",
            base_currency="USD",
            positions=[Position(instrument_id="GBP_STK", quantity=Decimal("10"))],
            cash_balances=[],
        )
        mkt = MarketDataSnapshot(
            prices=[
                Price(instrument_id="GBP_STK", price=Decimal("100"), currency="GBP"),
                Price(instrument_id="GBP_STK_B", price=Decimal("100"), currency="GBP"),
            ],
            fx_rates=[FxRate(pair="GBP/USD", rate=Decimal("1.2"))],
        )
        shelf = [
            ShelfEntry(instrument_id="GBP_STK", status="APPROVED"),
            ShelfEntry(instrument_id="GBP_STK_B", status="APPROVED"),
        ]
        model = ModelPortfolio(
            targets=[
                ModelTarget(instrument_id="GBP_STK_B", weight=Decimal("1.0")),
                ModelTarget(instrument_id="GBP_STK", weight=Decimal("0.0")),
            ]
        )

        result = run_simulation(pf, mkt, model, shelf, EngineOptions())

        buy = next(i for i in result.intents if i.instrument_id == "GBP_STK_B")
        sell = next(i for i in result.intents if i.instrument_id == "GBP_STK")
        assert sell.intent_id in buy.dependencies

    def test_generate_fx_and_simulate_blocks_on_missing_fx_when_enabled(self):
        pf = PortfolioSnapshot(
            portfolio_id="pf_fx_block",
            base_currency="USD",
            positions=[],
            cash_balances=[CashBalance(currency="EUR", amount=Decimal("100"))],
        )
        diagnostics = empty_diagnostics()

        intents, after, rules, status, recon = _generate_fx_and_simulate(
            portfolio=pf,
            market_data=MarketDataSnapshot(prices=[], fx_rates=[]),
            shelf=[],
            intents=[],
            options=EngineOptions(block_on_missing_fx=True),
            total_val_before=Decimal("0"),
            diagnostics=diagnostics,
        )

        assert status == "BLOCKED"
        assert rules == []
        assert recon is None
        assert intents == []
        assert after.portfolio_id == pf.portfolio_id
        assert diagnostics.data_quality["fx_missing"] == ["EUR/USD"]

    def test_generate_fx_and_simulate_continues_on_missing_fx_when_disabled(self):
        diagnostics = empty_diagnostics()

        _, _, _, status, _ = _generate_fx_and_simulate(
            portfolio=PortfolioSnapshot(
                portfolio_id="pf_fx_continue",
                base_currency="USD",
                positions=[],
                cash_balances=[CashBalance(currency="EUR", amount=Decimal("100"))],
            ),
            market_data=MarketDataSnapshot(prices=[], fx_rates=[]),
            shelf=[],
            intents=[],
            options=EngineOptions(block_on_missing_fx=False),
            total_val_before=Decimal("0"),
            diagnostics=diagnostics,
        )

        assert status in {"READY", "PENDING_REVIEW"}
        assert diagnostics.data_quality["fx_missing"].count("EUR/USD") >= 1
