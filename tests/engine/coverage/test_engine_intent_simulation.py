from decimal import Decimal

from src.core.engine import _generate_fx_and_simulate, run_simulation
from src.core.models import (
    EngineOptions,
)
from tests.assertions import security_intents
from tests.engine.coverage.helpers import empty_diagnostics, usd_cash_portfolio
from tests.factories import (
    cash,
    fx,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
    target,
)


class TestIntentDependenciesAndSimulation:
    def test_dependency_linking_explicit(self):
        pf = usd_cash_portfolio("dep_test")
        mkt = market_data_snapshot(
            prices=[price("GBP_STK", "100", "GBP")],
            fx_rates=[fx("GBP/USD", "1.2")],
        )
        shelf = [shelf_entry("GBP_STK", status="APPROVED")]
        model = model_portfolio(targets=[target("GBP_STK", "1.0")])

        result = run_simulation(pf, mkt, model, shelf, EngineOptions())

        buy = next(i for i in security_intents(result) if i.side == "BUY")
        assert len(buy.dependencies) > 0

    def test_dependency_sell_linking(self):
        pf = portfolio_snapshot(
            portfolio_id="p_chain",
            base_currency="USD",
            positions=[position("GBP_STK", "10")],
        )
        mkt = market_data_snapshot(
            prices=[
                price("GBP_STK", "100", "GBP"),
                price("GBP_STK_B", "100", "GBP"),
            ],
            fx_rates=[fx("GBP/USD", "1.2")],
        )
        shelf = [
            shelf_entry("GBP_STK", status="APPROVED"),
            shelf_entry("GBP_STK_B", status="APPROVED"),
        ]
        model = model_portfolio(targets=[target("GBP_STK_B", "1.0"), target("GBP_STK", "0.0")])

        result = run_simulation(pf, mkt, model, shelf, EngineOptions())

        buy = next(i for i in security_intents(result) if i.instrument_id == "GBP_STK_B")
        sell = next(i for i in security_intents(result) if i.instrument_id == "GBP_STK")
        assert sell.intent_id in buy.dependencies

    def test_generate_fx_and_simulate_blocks_on_missing_fx_when_enabled(self):
        pf = portfolio_snapshot(
            portfolio_id="pf_fx_block",
            base_currency="USD",
            cash_balances=[cash("EUR", "100")],
        )
        diagnostics = empty_diagnostics()

        intents, after, rules, status, recon = _generate_fx_and_simulate(
            portfolio=pf,
            market_data=market_data_snapshot(prices=[], fx_rates=[]),
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
            portfolio=portfolio_snapshot(
                portfolio_id="pf_fx_continue",
                base_currency="USD",
                cash_balances=[cash("EUR", "100")],
            ),
            market_data=market_data_snapshot(prices=[], fx_rates=[]),
            shelf=[],
            intents=[],
            options=EngineOptions(block_on_missing_fx=False),
            total_val_before=Decimal("0"),
            diagnostics=diagnostics,
        )

        assert status in {"READY", "PENDING_REVIEW"}
        assert diagnostics.data_quality["fx_missing"].count("EUR/USD") >= 1
