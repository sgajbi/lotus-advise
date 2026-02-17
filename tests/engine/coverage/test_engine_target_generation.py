from decimal import Decimal

from src.core.engine import _generate_targets, run_simulation
from src.core.models import EngineOptions
from tests.assertions import assert_status
from tests.factories import model_portfolio, position, target


class TestTargetGeneration:
    def test_target_locked_over_100(self, base_inputs):
        pf, mkt, model, shelf = base_inputs
        pf.positions = [position("LOCKED_ASSET", "1000")]
        mkt.prices[0].price = Decimal("1000")

        result = run_simulation(pf, mkt, model, shelf, EngineOptions())

        assert_status(result, "PENDING_REVIEW")

    def test_min_cash_buffer_scaling(self, base_inputs):
        pf, mkt, _, shelf = base_inputs
        model = model_portfolio(targets=[target("TARGET_ASSET", "1.0")])

        result = run_simulation(
            pf, mkt, model, shelf, EngineOptions(min_cash_buffer_pct=Decimal("0.10"))
        )

        tgt = next(t for t in result.target.targets if t.instrument_id == "TARGET_ASSET")
        assert tgt.final_weight <= Decimal("0.91")
        assert_status(result, "PENDING_REVIEW")

    def test_generate_targets_marks_pending_when_redistribution_remainder_stays(self):
        model = model_portfolio(targets=[target("B1", "0.2313"), target("B2", "0.4895")])
        eligible_targets = {
            "B1": Decimal("0.2313"),
            "B2": Decimal("0.4895"),
            "L1": Decimal("0.5266"),
            "L2": Decimal("0.0933"),
        }

        _, status = _generate_targets(
            model=model,
            eligible_targets=eligible_targets,
            buy_list=["B1", "B2"],
            sell_only_excess=Decimal("0.0"),
            options=EngineOptions(single_position_max_weight=Decimal("0.5")),
            total_val=Decimal("100"),
            base_ccy="USD",
        )

        assert status == "PENDING_REVIEW"
