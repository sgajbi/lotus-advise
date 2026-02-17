from decimal import Decimal

from src.core.engine import run_simulation
from src.core.models import (
    CashBalance,
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    Position,
    Price,
    ShelfEntry,
)
from src.core.valuation import build_simulated_state
from tests.engine.coverage.helpers import usd_cash_portfolio


class TestUniverseAndDataQuality:
    def test_engine_restricted_logic(self, base_inputs):
        pf, mkt, model, shelf = base_inputs
        result = run_simulation(pf, mkt, model, shelf, EngineOptions(allow_restricted=False))
        excl = next(
            (e for e in result.universe.excluded if e.instrument_id == "LOCKED_ASSET"), None
        )
        assert excl is not None
        assert "LOCKED_DUE_TO_RESTRICTED" in excl.reason_code

    def test_universe_suspended_exclusion(self, base_inputs):
        pf, mkt, _, shelf = base_inputs
        model = ModelPortfolio(
            targets=[ModelTarget(instrument_id="SUSPENDED_ASSET", weight=Decimal("0.1"))]
        )
        shelf.append(ShelfEntry(instrument_id="SUSPENDED_ASSET", status="SUSPENDED"))

        result = run_simulation(pf, mkt, model, shelf, EngineOptions())

        excl = next(
            (e for e in result.universe.excluded if e.instrument_id == "SUSPENDED_ASSET"), None
        )
        assert excl is not None
        assert "SHELF_STATUS_SUSPENDED" in excl.reason_code

    def test_universe_missing_shelf_locked(self, base_inputs):
        pf, mkt, model, shelf = base_inputs
        pf.positions.append(Position(instrument_id="GHOST_ASSET", quantity=Decimal("10")))
        mkt.prices.append(Price(instrument_id="GHOST_ASSET", price=Decimal("100"), currency="USD"))

        result = run_simulation(pf, mkt, model, shelf, EngineOptions())

        excl = next((e for e in result.universe.excluded if e.instrument_id == "GHOST_ASSET"), None)
        assert excl is not None
        assert "LOCKED_DUE_TO_MISSING_SHELF" in excl.reason_code

    def test_blocked_when_model_target_missing_from_shelf(self):
        pf = usd_cash_portfolio("pf_missing_shelf")
        mkt = MarketDataSnapshot(
            prices=[Price(instrument_id="MODEL_ONLY", price=Decimal("10"), currency="USD")],
            fx_rates=[],
        )
        model = ModelPortfolio(
            targets=[ModelTarget(instrument_id="MODEL_ONLY", weight=Decimal("1.0"))]
        )

        result = run_simulation(pf, mkt, model, shelf=[], options=EngineOptions())

        assert result.status == "BLOCKED"
        assert result.diagnostics.data_quality["shelf_missing"] == ["MODEL_ONLY"]

    def test_valuation_missing_fx_log(self, base_inputs):
        pf, mkt, _, shelf = base_inputs
        pf.positions.append(Position(instrument_id="NO_FX_ASSET", quantity=Decimal("10")))
        mkt.prices.append(Price(instrument_id="NO_FX_ASSET", price=Decimal("100"), currency="KRW"))
        pf.cash_balances.append(CashBalance(currency="KRW", amount=Decimal("500")))
        dq = {}
        warns = []

        build_simulated_state(pf, mkt, shelf, dq, warns)

        assert "KRW/USD" in dq["fx_missing"]
