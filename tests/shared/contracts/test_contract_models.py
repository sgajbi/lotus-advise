"""
FILE: tests/contracts/test_contract_models.py
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.core.models import (
    AllocationMetric,
    BatchRebalanceRequest,
    BatchScenarioMetric,
    DiagnosticsData,
    EngineOptions,
    GroupConstraint,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    Money,
    PortfolioSnapshot,
    Position,
    Price,
    ProposedTrade,
    ShelfEntry,
    SimulatedState,
    SimulationScenario,
    TargetMethod,
    TaxLot,
)


def test_money_validation():
    m = Money(amount=Decimal("100.00"), currency="USD")
    assert m.amount == Decimal("100.00")
    assert m.currency == "USD"

    with pytest.raises(ValidationError):
        Money(amount="invalid", currency="USD")


def test_shelf_entry_status_validation():
    # Valid status
    s = ShelfEntry(instrument_id="AAPL", status="APPROVED")
    assert s.status == "APPROVED"

    # Invalid status
    with pytest.raises(ValidationError):
        ShelfEntry(instrument_id="AAPL", status="INVALID_STATUS")


def test_shelf_entry_attributes():
    # Test attribute tagging support (RFC-0008)
    s = ShelfEntry(
        instrument_id="AAPL",
        status="APPROVED",
        attributes={"sector": "TECH", "region": "US"},
    )
    assert s.attributes["sector"] == "TECH"
    assert s.attributes["region"] == "US"
    assert len(s.attributes) == 2


def test_simulated_state_structure():
    # Ensure compatibility with new allocation_by_attribute field
    state = SimulatedState(
        total_value=Money(amount=Decimal("100"), currency="USD"),
        positions=[],
        cash_balances=[],
        allocation_by_asset_class=[],
        allocation_by_instrument=[],
        allocation=[],
        allocation_by_attribute={"sector": []},
    )
    assert "sector" in state.allocation_by_attribute


def test_group_constraint_max_weight_bounds_validation():
    EngineOptions(group_constraints={"sector:TECH": GroupConstraint(max_weight=Decimal("0.5"))})

    with pytest.raises(ValidationError):
        GroupConstraint(max_weight=Decimal("-0.01"))
    with pytest.raises(ValidationError):
        GroupConstraint(max_weight=Decimal("1.01"))


def test_group_constraint_key_format_validation():
    with pytest.raises(ValidationError):
        EngineOptions(group_constraints={"sectorTECH": GroupConstraint(max_weight=Decimal("0.5"))})
    with pytest.raises(ValidationError):
        EngineOptions(group_constraints={":TECH": GroupConstraint(max_weight=Decimal("0.5"))})
    with pytest.raises(ValidationError):
        EngineOptions(group_constraints={"sector:": GroupConstraint(max_weight=Decimal("0.5"))})


def test_diagnostics_supports_group_constraint_events():
    diag = DiagnosticsData(
        warnings=[],
        suppressed_intents=[],
        dropped_intents=[],
        group_constraint_events=[],
        data_quality={"price_missing": [], "fx_missing": [], "shelf_missing": []},
    )
    assert diag.group_constraint_events == []


def test_diagnostics_supports_dropped_intents():
    diag = DiagnosticsData(
        warnings=[],
        suppressed_intents=[],
        dropped_intents=[],
        group_constraint_events=[],
        data_quality={"price_missing": [], "fx_missing": [], "shelf_missing": []},
    )
    assert diag.dropped_intents == []


def test_diagnostics_supports_advisory_funding_fields():
    diag = DiagnosticsData(
        warnings=[],
        suppressed_intents=[],
        dropped_intents=[],
        group_constraint_events=[],
        data_quality={"price_missing": [], "fx_missing": [], "shelf_missing": []},
    )
    assert diag.missing_fx_pairs == []
    assert diag.funding_plan == []
    assert diag.insufficient_cash == []


def test_target_method_defaults_to_heuristic():
    options = EngineOptions()
    assert options.target_method == TargetMethod.HEURISTIC


def test_target_method_comparison_options_defaults():
    options = EngineOptions()
    assert options.compare_target_methods is False
    assert options.compare_target_methods_tolerance == Decimal("0.0001")
    assert options.enable_workflow_gates is True
    assert options.workflow_requires_client_consent is False
    assert options.client_consent_already_obtained is False


def test_max_turnover_pct_validation_bounds():
    opts = EngineOptions(max_turnover_pct=Decimal("0.15"))
    assert opts.max_turnover_pct == Decimal("0.15")

    with pytest.raises(ValidationError):
        EngineOptions(max_turnover_pct=Decimal("-0.01"))
    with pytest.raises(ValidationError):
        EngineOptions(max_turnover_pct=Decimal("1.01"))


def test_max_turnover_pct_accepts_none():
    opts = EngineOptions(max_turnover_pct=None)
    assert opts.max_turnover_pct is None


def test_settlement_awareness_options_defaults_and_bounds():
    options = EngineOptions()
    assert options.enable_tax_awareness is False
    assert options.max_realized_capital_gains is None
    assert options.enable_settlement_awareness is False
    assert options.settlement_horizon_days == 5
    assert options.fx_settlement_days == 2
    assert options.max_overdraft_by_ccy == {}

    with pytest.raises(ValidationError):
        EngineOptions(settlement_horizon_days=11)
    with pytest.raises(ValidationError):
        EngineOptions(fx_settlement_days=-1)


def test_max_overdraft_by_ccy_rejects_negative_values():
    with pytest.raises(ValidationError):
        EngineOptions(max_overdraft_by_ccy={"USD": Decimal("-1")})


def test_max_overdraft_by_ccy_rejects_empty_currency_key():
    with pytest.raises(ValidationError):
        EngineOptions(max_overdraft_by_ccy={"": Decimal("1")})


def test_tax_lot_quantity_must_match_position_quantity_within_tolerance():
    Position(
        instrument_id="EQ_1",
        quantity=Decimal("100"),
        lots=[
            TaxLot(
                lot_id="L1",
                quantity=Decimal("50"),
                unit_cost=Money(amount=Decimal("10"), currency="USD"),
                purchase_date="2025-01-01",
            ),
            TaxLot(
                lot_id="L2",
                quantity=Decimal("50"),
                unit_cost=Money(amount=Decimal("12"), currency="USD"),
                purchase_date="2025-02-01",
            ),
        ],
    )

    with pytest.raises(ValidationError):
        Position(
            instrument_id="EQ_1",
            quantity=Decimal("100"),
            lots=[
                TaxLot(
                    lot_id="L1",
                    quantity=Decimal("60"),
                    unit_cost=Money(amount=Decimal("10"), currency="USD"),
                    purchase_date="2025-01-01",
                ),
                TaxLot(
                    lot_id="L2",
                    quantity=Decimal("30"),
                    unit_cost=Money(amount=Decimal("12"), currency="USD"),
                    purchase_date="2025-02-01",
                ),
            ],
        )


def test_batch_request_requires_at_least_one_scenario():
    with pytest.raises(ValidationError):
        BatchRebalanceRequest(
            portfolio_snapshot=PortfolioSnapshot(portfolio_id="pf", base_currency="USD"),
            market_data_snapshot=MarketDataSnapshot(
                prices=[Price(instrument_id="EQ_1", price=Decimal("100"), currency="USD")],
                fx_rates=[],
            ),
            model_portfolio=ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=1)]),
            shelf_entries=[ShelfEntry(instrument_id="EQ_1", status="APPROVED")],
            scenarios={},
        )


def test_batch_request_validates_scenario_name_format():
    with pytest.raises(ValidationError):
        BatchRebalanceRequest(
            portfolio_snapshot=PortfolioSnapshot(portfolio_id="pf", base_currency="USD"),
            market_data_snapshot=MarketDataSnapshot(
                prices=[Price(instrument_id="EQ_1", price=Decimal("100"), currency="USD")],
                fx_rates=[],
            ),
            model_portfolio=ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=1)]),
            shelf_entries=[ShelfEntry(instrument_id="EQ_1", status="APPROVED")],
            scenarios={"Invalid-Name": SimulationScenario(options={})},
        )


def test_batch_request_rejects_case_insensitive_duplicate_scenario_keys():
    with pytest.raises(ValidationError):
        BatchRebalanceRequest(
            portfolio_snapshot=PortfolioSnapshot(portfolio_id="pf", base_currency="USD"),
            market_data_snapshot=MarketDataSnapshot(
                prices=[Price(instrument_id="EQ_1", price=Decimal("100"), currency="USD")],
                fx_rates=[],
            ),
            model_portfolio=ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=1)]),
            shelf_entries=[ShelfEntry(instrument_id="EQ_1", status="APPROVED")],
            scenarios={
                "base": SimulationScenario(options={}),
                "BASE": SimulationScenario(options={}),
            },
        )


def test_snapshot_models_accept_snapshot_id():
    portfolio = PortfolioSnapshot(snapshot_id="ps_1", portfolio_id="pf", base_currency="USD")
    market = MarketDataSnapshot(
        snapshot_id="md_1",
        prices=[Price(instrument_id="EQ_1", price=Decimal("100"), currency="USD")],
        fx_rates=[],
    )
    assert portfolio.snapshot_id == "ps_1"
    assert market.snapshot_id == "md_1"


def test_batch_request_enforces_max_scenario_count():
    scenarios = {f"s{i}": SimulationScenario(options={}) for i in range(21)}
    with pytest.raises(ValidationError):
        BatchRebalanceRequest(
            portfolio_snapshot=PortfolioSnapshot(portfolio_id="pf", base_currency="USD"),
            market_data_snapshot=MarketDataSnapshot(
                prices=[Price(instrument_id="EQ_1", price=Decimal("100"), currency="USD")],
                fx_rates=[],
            ),
            model_portfolio=ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=1)]),
            shelf_entries=[ShelfEntry(instrument_id="EQ_1", status="APPROVED")],
            scenarios=scenarios,
        )


def test_batch_scenario_metric_shape():
    metric = BatchScenarioMetric(
        status="READY",
        security_intent_count=2,
        gross_turnover_notional_base=Money(amount=Decimal("1500"), currency="USD"),
    )
    assert metric.status == "READY"
    assert metric.security_intent_count == 2
    assert metric.gross_turnover_notional_base.amount == Decimal("1500")


def test_batch_scenario_metric_rejects_invalid_status():
    with pytest.raises(ValidationError):
        BatchScenarioMetric(
            status="UNKNOWN",
            security_intent_count=1,
            gross_turnover_notional_base=Money(amount=Decimal("10"), currency="USD"),
        )


def test_suitability_thresholds_validate_liquidity_tier_keys():
    with pytest.raises(ValidationError):
        EngineOptions(suitability_thresholds={"max_weight_by_liquidity_tier": {"L9": "0.10"}})


def test_suitability_thresholds_validate_cash_band_order():
    with pytest.raises(ValidationError):
        EngineOptions(
            suitability_thresholds={
                "cash_band_min_weight": "0.10",
                "cash_band_max_weight": "0.05",
            }
        )


def test_suitability_thresholds_validate_liquidity_tier_values():
    with pytest.raises(ValidationError):
        EngineOptions(suitability_thresholds={"max_weight_by_liquidity_tier": {"L4": "1.01"}})


def test_proposed_trade_notional_validators_reject_float_and_non_positive():
    with pytest.raises(ValidationError):
        ProposedTrade.model_validate(
            {
                "side": "BUY",
                "instrument_id": "EQ_1",
                "notional": {"amount": 10.5, "currency": "USD"},
            }
        )

    with pytest.raises(ValidationError):
        ProposedTrade.model_validate(
            {
                "side": "BUY",
                "instrument_id": "EQ_1",
                "notional": {"amount": "0", "currency": "USD"},
            }
        )


def test_allocation_metric_weight_serialization_is_quantized():
    metric = AllocationMetric(
        key="EQ_1",
        weight=Decimal("0.6666666666666666666666666667"),
        value=Money(amount=Decimal("100"), currency="USD"),
    )
    payload = metric.model_dump(mode="json")
    assert payload["weight"] == "0.6667"
