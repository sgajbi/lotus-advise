from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.core.models import (
    CashFlowIntent,
    EngineOptions,
    FxSpotIntent,
    IntentRationale,
    LineageData,
    MarketDataSnapshot,
    Money,
    PortfolioSnapshot,
    ProposalResult,
    ProposalSimulateRequest,
    ProposedCashFlow,
    ProposedTrade,
    Reconciliation,
    RuleResult,
    ShelfEntry,
    SimulatedState,
)


def test_advisory_engine_options_defaults():
    options = EngineOptions()
    assert options.enable_proposal_simulation is False
    assert options.proposal_apply_cash_flows_first is True
    assert options.proposal_block_negative_cash is True
    assert options.enable_drift_analytics is True
    assert options.enable_instrument_drift is True
    assert options.drift_top_contributors_limit == 5
    assert options.drift_unmodeled_exposure_threshold == Decimal("0.01")
    assert options.auto_funding is True
    assert options.funding_mode == "AUTO_FX"
    assert options.fx_funding_source_currency == "ANY_CASH"
    assert options.fx_generation_policy == "ONE_FX_PER_CCY"


def test_advisory_proposed_trade_requires_quantity_or_notional():
    with pytest.raises(ValidationError):
        ProposedTrade(side="BUY", instrument_id="EQ_1")


def test_advisory_proposed_trade_rejects_quantity_and_notional_together():
    with pytest.raises(ValidationError):
        ProposedTrade(
            side="BUY",
            instrument_id="EQ_1",
            quantity=Decimal("1"),
            notional={"amount": "100", "currency": "USD"},
        )


def test_advisory_proposed_trade_rejects_float_quantity():
    with pytest.raises(ValidationError):
        ProposedTrade(side="BUY", instrument_id="EQ_1", quantity=1.25)


def test_advisory_proposed_cash_flow_rejects_float_amount():
    with pytest.raises(ValidationError):
        ProposedCashFlow(currency="USD", amount=10.5)


def test_advisory_proposal_request_shape():
    request = ProposalSimulateRequest(
        portfolio_snapshot=PortfolioSnapshot(portfolio_id="pf", base_currency="USD"),
        market_data_snapshot=MarketDataSnapshot(prices=[], fx_rates=[]),
        shelf_entries=[ShelfEntry(instrument_id="EQ_1", status="APPROVED")],
        reference_model={
            "model_id": "mdl_1",
            "as_of": "2026-02-18",
            "base_currency": "USD",
            "asset_class_targets": [{"asset_class": "CASH", "weight": "1.0"}],
        },
        proposed_cash_flows=[ProposedCashFlow(currency="USD", amount=Decimal("100"))],
        proposed_trades=[ProposedTrade(side="BUY", instrument_id="EQ_1", quantity=Decimal("1"))],
    )
    assert request.proposed_cash_flows[0].intent_type == "CASH_FLOW"
    assert request.proposed_trades[0].intent_type == "SECURITY_TRADE"
    assert request.reference_model.model_id == "mdl_1"


def test_advisory_proposal_result_accepts_fx_spot_intents():
    state = SimulatedState(
        total_value=Money(amount=Decimal("1000"), currency="USD"),
        cash_balances=[],
        positions=[],
        allocation_by_asset_class=[],
        allocation_by_instrument=[],
        allocation=[],
        allocation_by_attribute={},
    )
    result = ProposalResult(
        proposal_run_id="pr_test",
        correlation_id="corr_test",
        status="READY",
        before=state,
        intents=[
            CashFlowIntent(intent_id="oi_cf_1", currency="USD", amount=Decimal("10")),
            FxSpotIntent(
                intent_id="oi_fx_1",
                pair="EUR/USD",
                buy_currency="EUR",
                buy_amount=Decimal("100"),
                sell_currency="USD",
                sell_amount_estimated=Decimal("110"),
                rationale=IntentRationale(code="FUNDING", message="Fund EUR buys"),
            ),
        ],
        after_simulated=state,
        reconciliation=Reconciliation(
            before_total_value=Money(amount=Decimal("1000"), currency="USD"),
            after_total_value=Money(amount=Decimal("1000"), currency="USD"),
            delta=Money(amount=Decimal("0"), currency="USD"),
            tolerance=Money(amount=Decimal("1"), currency="USD"),
            status="OK",
        ),
        rule_results=[
            RuleResult(
                rule_id="DATA_QUALITY",
                severity="HARD",
                status="PASS",
                measured=Decimal("0"),
                threshold={"max": Decimal("0")},
                reason_code="OK",
            )
        ],
        explanation={"summary": "READY"},
        diagnostics={"data_quality": {"price_missing": [], "fx_missing": [], "shelf_missing": []}},
        lineage=LineageData(
            portfolio_snapshot_id="pf",
            market_data_snapshot_id="md",
            request_hash="hash",
        ),
    )

    assert result.intents[1].intent_type == "FX_SPOT"
