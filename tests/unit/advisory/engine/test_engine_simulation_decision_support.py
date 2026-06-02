from src.core.advisory.simulation_decision_support import build_simulation_decision_support
from src.core.advisory.simulation_intent_plan import SimulationIntentPlan
from src.core.common.diagnostics import make_diagnostics_data
from src.core.models import EngineOptions, ReferenceModel
from src.core.valuation import build_simulated_state
from tests.shared.factories import cash, market_data_snapshot, portfolio_snapshot


def _state(portfolio_id: str = "pf_simulation_decision_support"):
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
    intent_plan = SimulationIntentPlan(
        after_portfolio=portfolio,
        cash_flows=[],
        trades=[],
        intents=[],
        hard_failures=[],
        force_pending_review=False,
    )
    return portfolio, market_data, diagnostics, before, intent_plan


def test_decision_support_records_reference_model_currency_mismatch():
    portfolio, market_data, diagnostics, before, intent_plan = _state(
        "pf_decision_support_ref_mismatch"
    )

    support = build_simulation_decision_support(
        portfolio=portfolio,
        market_data=market_data,
        shelf=[],
        options=EngineOptions(enable_proposal_simulation=True),
        diagnostics=diagnostics,
        before=before,
        after=before,
        intent_plan=intent_plan,
        final_status="READY",
        rule_results=[],
        reference_model=ReferenceModel(
            model_id="mdl_sgd",
            as_of="2026-02-19",
            base_currency="SGD",
        ),
        policy_context=None,
    )

    assert support.drift_analysis is None
    assert diagnostics.warnings == ["REFERENCE_MODEL_BASE_CURRENCY_MISMATCH"]


def test_decision_support_respects_disabled_optional_outputs():
    portfolio, market_data, diagnostics, before, intent_plan = _state(
        "pf_decision_support_disabled"
    )

    support = build_simulation_decision_support(
        portfolio=portfolio,
        market_data=market_data,
        shelf=[],
        options=EngineOptions(
            enable_proposal_simulation=True,
            enable_drift_analytics=False,
            enable_suitability_scanner=False,
            enable_workflow_gates=False,
        ),
        diagnostics=diagnostics,
        before=before,
        after=before,
        intent_plan=intent_plan,
        final_status="READY",
        rule_results=[],
        reference_model=None,
        policy_context=None,
    )

    assert support.drift_analysis is None
    assert support.suitability is None
    assert support.gate_decision is None
