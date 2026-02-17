from decimal import Decimal

from src.core.engine import run_simulation
from src.core.models import EngineOptions, Money, Position, Price, ShelfEntry, ValuationMode


class TestFinalStatusAndBlocking:
    def test_reconciliation_failure_block(self, base_inputs):
        pf, mkt, model, shelf = base_inputs
        pf.positions[0].market_value = Money(amount=Decimal("9999999"), currency="USD")

        result = run_simulation(
            pf,
            mkt,
            model,
            shelf,
            EngineOptions(valuation_mode=ValuationMode.TRUST_SNAPSHOT),
        )

        assert result.status == "BLOCKED"
        blocker = next(r for r in result.rule_results if r.rule_id == "RECONCILIATION")
        assert blocker.status == "FAIL"

    def test_hard_fail_shorting(self, base_inputs):
        pf, mkt, model, shelf = base_inputs
        pf.positions.append(Position(instrument_id="SHORT_POS", quantity=Decimal("-10")))
        mkt.prices.append(Price(instrument_id="SHORT_POS", price=Decimal("100"), currency="USD"))
        shelf.append(ShelfEntry(instrument_id="SHORT_POS", status="APPROVED"))

        result = run_simulation(pf, mkt, model, shelf, EngineOptions())

        assert result.status == "BLOCKED"
        assert "SIMULATION_SAFETY_CHECK_FAILED" in result.diagnostics.warnings

    def test_soft_fail_status(self, base_inputs):
        pf, mkt, model, shelf = base_inputs
        result = run_simulation(
            pf, mkt, model, shelf, EngineOptions(cash_band_min_weight=Decimal("0.05"))
        )

        assert result.status == "PENDING_REVIEW"
