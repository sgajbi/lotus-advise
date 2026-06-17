from decimal import Decimal
from unittest.mock import patch

from src.core.advisory.simulation_intent_plan import SimulationIntentPlan
from src.core.advisory.simulation_review import evaluate_simulation_review
from src.core.common.diagnostics import make_diagnostics_data
from src.core.models import EngineOptions, Money, Reconciliation
from src.core.valuation import build_simulated_state
from tests.shared.factories import cash, market_data_snapshot, portfolio_snapshot


def _state(portfolio_id: str = "pf_simulation_review"):
    portfolio = portfolio_snapshot(
        portfolio_id=portfolio_id,
        base_currency="USD",
        positions=[],
        cash_balances=[cash("USD", "1000")],
    )
    market_data = market_data_snapshot(prices=[], fx_rates=[])
    diagnostics = make_diagnostics_data()
    before = build_simulated_state(
        portfolio,
        market_data,
        [],
        diagnostics.data_quality,
        diagnostics.warnings,
        EngineOptions(enable_proposal_simulation=True),
    )
    return portfolio, market_data, diagnostics, before


def test_simulation_review_forces_pending_review_for_funding_dq():
    portfolio, market_data, diagnostics, before = _state("pf_simulation_review_funding_dq")
    diagnostics.missing_fx_pairs.append("USD/SGD")
    intent_plan = SimulationIntentPlan(
        after_portfolio=portfolio,
        cash_flows=[],
        trades=[],
        intents=[],
        hard_failures=[],
        force_pending_review=True,
    )

    with patch(
        "src.core.advisory.simulation_review.derive_status_from_rules",
        return_value="READY",
    ):
        review = evaluate_simulation_review(
            portfolio=portfolio,
            market_data=market_data,
            options=EngineOptions(enable_proposal_simulation=True),
            diagnostics=diagnostics,
            before=before,
            after=before,
            intent_plan=intent_plan,
        )

    assert review.final_status == "PENDING_REVIEW"
    assert any(rule.rule_id == "PROPOSAL_FUNDING_DQ" for rule in review.rule_results)


def test_simulation_review_records_input_guard_hard_failure():
    portfolio, market_data, diagnostics, before = _state("pf_simulation_review_input_guard")
    intent_plan = SimulationIntentPlan(
        after_portfolio=portfolio,
        cash_flows=[],
        trades=[],
        intents=[],
        hard_failures=["PROPOSAL_INVALID_TRADE_INPUT"],
        force_pending_review=False,
    )

    review = evaluate_simulation_review(
        portfolio=portfolio,
        market_data=market_data,
        options=EngineOptions(enable_proposal_simulation=True),
        diagnostics=diagnostics,
        before=before,
        after=before,
        intent_plan=intent_plan,
    )

    input_guard_rule = next(
        rule for rule in review.rule_results if rule.rule_id == "PROPOSAL_INPUT_GUARDS"
    )
    assert review.final_status == "BLOCKED"
    assert input_guard_rule.status == "FAIL"
    assert input_guard_rule.severity == "HARD"
    assert input_guard_rule.measured == 1
    assert input_guard_rule.threshold == {"max": Decimal("0")}
    assert input_guard_rule.reason_code == "PROPOSAL_INVALID_TRADE_INPUT"


def test_simulation_review_blocks_reconciliation_mismatch():
    portfolio, market_data, diagnostics, before = _state("pf_simulation_review_recon")
    intent_plan = SimulationIntentPlan(
        after_portfolio=portfolio,
        cash_flows=[],
        trades=[],
        intents=[],
        hard_failures=[],
        force_pending_review=False,
    )

    with patch(
        "src.core.advisory.simulation_review.build_reconciliation",
        return_value=(
            Reconciliation(
                before_total_value=Money(amount=Decimal("1000"), currency="USD"),
                after_total_value=Money(amount=Decimal("900"), currency="USD"),
                delta=Money(amount=Decimal("-100"), currency="USD"),
                tolerance=Money(amount=Decimal("0"), currency="USD"),
                status="MISMATCH",
            ),
            Decimal("100"),
            Decimal("0"),
        ),
    ):
        review = evaluate_simulation_review(
            portfolio=portfolio,
            market_data=market_data,
            options=EngineOptions(enable_proposal_simulation=True),
            diagnostics=diagnostics,
            before=before,
            after=before,
            intent_plan=intent_plan,
        )

    assert review.final_status == "BLOCKED"
    assert any(rule.rule_id == "RECONCILIATION" for rule in review.rule_results)
