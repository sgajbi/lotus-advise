"""
FILE: tests/contracts/test_contract_models.py
"""

import ast
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.core.diagnostics_models import (
    CashLadderBreach as DiagnosticsCashLadderBreach,
)
from src.core.diagnostics_models import (
    CashLadderPoint as DiagnosticsCashLadderPoint,
)
from src.core.diagnostics_models import (
    DiagnosticsData as DiagnosticsDiagnosticsData,
)
from src.core.diagnostics_models import (
    DroppedIntent as DiagnosticsDroppedIntent,
)
from src.core.diagnostics_models import (
    FundingPlanEntry as DiagnosticsFundingPlanEntry,
)
from src.core.diagnostics_models import (
    GroupConstraintEvent as DiagnosticsGroupConstraintEvent,
)
from src.core.diagnostics_models import (
    InsufficientCashEntry as DiagnosticsInsufficientCashEntry,
)
from src.core.diagnostics_models import (
    LineageData as DiagnosticsLineageData,
)
from src.core.diagnostics_models import (
    RuleResult as DiagnosticsRuleResult,
)
from src.core.diagnostics_models import (
    SuppressedIntent as DiagnosticsSuppressedIntent,
)
from src.core.diagnostics_models import (
    TaxBudgetConstraintEvent as DiagnosticsTaxBudgetConstraintEvent,
)
from src.core.drift_models import (
    DriftAnalysis as DriftDriftAnalysis,
)
from src.core.drift_models import (
    DriftBucketDetail as DriftDriftBucketDetail,
)
from src.core.drift_models import (
    DriftDimensionAnalysis as DriftDriftDimensionAnalysis,
)
from src.core.drift_models import (
    DriftHighlightEntry as DriftDriftHighlightEntry,
)
from src.core.drift_models import (
    DriftHighlights as DriftDriftHighlights,
)
from src.core.drift_models import (
    DriftReferenceModelSummary as DriftDriftReferenceModelSummary,
)
from src.core.drift_models import (
    DriftUnmodeledExposure as DriftDriftUnmodeledExposure,
)
from src.core.engine_option_suitability_models import (
    GroupConstraint as SuitabilityGroupConstraint,
)
from src.core.engine_option_suitability_models import (
    SuitabilityThresholds as SuitabilitySuitabilityThresholds,
)
from src.core.engine_options_models import (
    EngineOptions as OptionsEngineOptions,
)
from src.core.engine_options_models import (
    GroupConstraint as OptionsGroupConstraint,
)
from src.core.engine_options_models import (
    SuitabilityThresholds as OptionsSuitabilityThresholds,
)
from src.core.engine_options_models import (
    TargetMethod as OptionsTargetMethod,
)
from src.core.engine_options_models import (
    ValuationMode as OptionsValuationMode,
)
from src.core.gate_models import (
    GateDecision as GateGateDecision,
)
from src.core.gate_models import (
    GateDecisionSummary as GateGateDecisionSummary,
)
from src.core.gate_models import (
    GateReason as GateGateReason,
)
from src.core.models import (
    AllocationMetric,
    CashBalance,
    CashFlowIntent,
    CashLadderBreach,
    CashLadderPoint,
    DiagnosticsData,
    DriftAnalysis,
    DriftBucketDetail,
    DriftDimensionAnalysis,
    DriftHighlightEntry,
    DriftHighlights,
    DriftReferenceModelSummary,
    DriftUnmodeledExposure,
    DroppedIntent,
    EngineOptions,
    ExcludedInstrument,
    FundingPlanEntry,
    FxSpotIntent,
    GateDecision,
    GateDecisionSummary,
    GateReason,
    GroupConstraint,
    GroupConstraintEvent,
    InsufficientCashEntry,
    IntentRationale,
    LineageData,
    MarketDataSnapshot,
    Money,
    OrderIntent,
    PortfolioSnapshot,
    Position,
    PositionSummary,
    Price,
    ProposalAllocationBucket,
    ProposalAllocationLens,
    ProposalAllocationView,
    ProposalOrderIntent,
    ProposalResult,
    ProposalSimulateRequest,
    ProposedCashFlow,
    ProposedTrade,
    Reconciliation,
    RuleResult,
    SecurityTradeIntent,
    ShelfEntry,
    SimulatedState,
    SuitabilityEvidence,
    SuitabilityEvidenceSnapshotIds,
    SuitabilityIssue,
    SuitabilityResult,
    SuitabilitySummary,
    SuitabilityThresholds,
    SuppressedIntent,
    TargetData,
    TargetInstrument,
    TargetMethod,
    TaxBudgetConstraintEvent,
    TaxImpact,
    TaxLot,
    UniverseCoverage,
    UniverseData,
    ValuationMode,
)
from src.core.order_intent_models import (
    CashFlowIntent as OrderCashFlowIntent,
)
from src.core.order_intent_models import (
    FxSpotIntent as OrderFxSpotIntent,
)
from src.core.order_intent_models import (
    IntentRationale as OrderIntentRationale,
)
from src.core.order_intent_models import (
    OrderIntent as OrderOrderIntent,
)
from src.core.order_intent_models import (
    ProposalOrderIntent as OrderProposalOrderIntent,
)
from src.core.order_intent_models import (
    SecurityTradeIntent as OrderSecurityTradeIntent,
)
from src.core.portfolio_models import (
    CashBalance as PortfolioCashBalance,
)
from src.core.portfolio_models import (
    MarketDataSnapshot as PortfolioMarketDataSnapshot,
)
from src.core.portfolio_models import (
    Money as PortfolioMoney,
)
from src.core.portfolio_models import (
    PortfolioSnapshot as PortfolioPortfolioSnapshot,
)
from src.core.portfolio_models import (
    Position as PortfolioPosition,
)
from src.core.portfolio_models import (
    Price as PortfolioPrice,
)
from src.core.portfolio_models import (
    ShelfEntry as PortfolioShelfEntry,
)
from src.core.portfolio_models import (
    TaxLot as PortfolioTaxLot,
)
from src.core.proposal_effect_models import (
    Reconciliation as EffectsReconciliation,
)
from src.core.proposal_effect_models import (
    TaxImpact as EffectsTaxImpact,
)
from src.core.proposal_request_models import (
    ProposalSimulateRequest as RequestProposalSimulateRequest,
)
from src.core.proposal_request_models import (
    ProposedCashFlow as RequestProposedCashFlow,
)
from src.core.proposal_request_models import (
    ProposedTrade as RequestProposedTrade,
)
from src.core.proposal_result_models import (
    ProposalResult as ResultProposalResult,
)
from src.core.simulation_state_models import (
    AllocationMetric as SimulationAllocationMetric,
)
from src.core.simulation_state_models import (
    PositionSummary as SimulationPositionSummary,
)
from src.core.simulation_state_models import (
    ProposalAllocationBucket as SimulationProposalAllocationBucket,
)
from src.core.simulation_state_models import (
    ProposalAllocationLens as SimulationProposalAllocationLens,
)
from src.core.simulation_state_models import (
    ProposalAllocationView as SimulationProposalAllocationView,
)
from src.core.simulation_state_models import (
    SimulatedState as SimulationSimulatedState,
)
from src.core.suitability_models import (
    SuitabilityEvidence as SuitabilitySuitabilityEvidence,
)
from src.core.suitability_models import (
    SuitabilityEvidenceSnapshotIds as SuitabilitySuitabilityEvidenceSnapshotIds,
)
from src.core.suitability_models import (
    SuitabilityIssue as SuitabilitySuitabilityIssue,
)
from src.core.suitability_models import (
    SuitabilityResult as SuitabilitySuitabilityResult,
)
from src.core.suitability_models import (
    SuitabilitySummary as SuitabilitySuitabilitySummary,
)
from src.core.universe_target_models import (
    ExcludedInstrument as UniverseExcludedInstrument,
)
from src.core.universe_target_models import (
    TargetData as UniverseTargetData,
)
from src.core.universe_target_models import (
    TargetInstrument as UniverseTargetInstrument,
)
from src.core.universe_target_models import (
    UniverseCoverage as UniverseUniverseCoverage,
)
from src.core.universe_target_models import (
    UniverseData as UniverseUniverseData,
)


def test_core_models_remains_compatibility_reexport_facade():
    source_path = Path(__file__).resolve().parents[4] / "src" / "core" / "models.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    inline_definitions = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert inline_definitions == []


def test_core_runtime_modules_use_focused_model_imports():
    source_root = Path(__file__).resolve().parents[4] / "src" / "core"
    runtime_modules = [
        source_root / "advisory_engine.py",
        source_root / "compliance.py",
        source_root / "target_generation.py",
        source_root / "valuation.py",
        source_root / "advisory" / "funding.py",
        source_root / "advisory" / "intents.py",
        source_root / "common" / "diagnostics.py",
        source_root / "common" / "drift_analytics.py",
        source_root / "common" / "intent_dependencies.py",
        source_root / "common" / "simulation_shared.py",
        source_root / "common" / "suitability.py",
        source_root / "common" / "workflow_gates.py",
    ]

    offenders = [
        str(path.relative_to(source_root.parents[1]))
        for path in runtime_modules
        if "from src.core.models import" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_proposal_workspace_modules_use_focused_model_imports():
    source_root = Path(__file__).resolve().parents[4] / "src" / "core"
    scan_roots = [
        source_root / "advisory",
        source_root / "proposals",
        source_root / "workspace",
    ]

    offenders = sorted(
        str(path.relative_to(source_root.parents[1]))
        for scan_root in scan_roots
        for path in scan_root.rglob("*.py")
        if "from src.core.models import" in path.read_text(encoding="utf-8")
    )

    assert offenders == []


def test_api_modules_use_focused_model_imports():
    source_root = Path(__file__).resolve().parents[4] / "src"
    api_root = source_root / "api"

    offenders = sorted(
        str(path.relative_to(source_root.parents[0]))
        for path in api_root.rglob("*.py")
        if "from src.core.models import" in path.read_text(encoding="utf-8")
    )

    assert offenders == []


def test_integration_modules_use_focused_model_imports():
    source_root = Path(__file__).resolve().parents[4] / "src"
    integrations_root = source_root / "integrations"

    offenders = sorted(
        str(path.relative_to(source_root.parents[0]))
        for path in integrations_root.rglob("*.py")
        if "from src.core.models import" in path.read_text(encoding="utf-8")
    )

    assert offenders == []


def test_core_models_preserves_portfolio_model_import_contract():
    assert Money is PortfolioMoney
    assert CashBalance is PortfolioCashBalance
    assert PortfolioSnapshot is PortfolioPortfolioSnapshot
    assert Position is PortfolioPosition
    assert Price is PortfolioPrice
    assert MarketDataSnapshot is PortfolioMarketDataSnapshot
    assert ShelfEntry is PortfolioShelfEntry
    assert TaxLot is PortfolioTaxLot


def test_core_models_preserves_engine_options_model_import_contract():
    assert EngineOptions is OptionsEngineOptions
    assert GroupConstraint is OptionsGroupConstraint
    assert SuitabilityThresholds is OptionsSuitabilityThresholds
    assert TargetMethod is OptionsTargetMethod
    assert ValuationMode is OptionsValuationMode


def test_engine_options_model_facade_delegates_suitability_models() -> None:
    engine_options_source = Path("src/core/engine_options_models.py").read_text(encoding="utf-8")
    suitability_source = Path("src/core/engine_option_suitability_models.py").read_text(
        encoding="utf-8"
    )

    assert OptionsGroupConstraint is SuitabilityGroupConstraint
    assert OptionsSuitabilityThresholds is SuitabilitySuitabilityThresholds
    assert "from src.core.engine_option_suitability_models import" in engine_options_source
    assert "class GroupConstraint(" not in engine_options_source
    assert "class SuitabilityThresholds(" not in engine_options_source
    assert "class GroupConstraint(" in suitability_source
    assert "class SuitabilityThresholds(" in suitability_source


def test_core_models_preserves_simulation_state_model_import_contract():
    assert AllocationMetric is SimulationAllocationMetric
    assert PositionSummary is SimulationPositionSummary
    assert ProposalAllocationBucket is SimulationProposalAllocationBucket
    assert ProposalAllocationLens is SimulationProposalAllocationLens
    assert ProposalAllocationView is SimulationProposalAllocationView
    assert SimulatedState is SimulationSimulatedState


def test_core_models_preserves_universe_target_model_import_contract():
    assert ExcludedInstrument is UniverseExcludedInstrument
    assert TargetData is UniverseTargetData
    assert TargetInstrument is UniverseTargetInstrument
    assert UniverseCoverage is UniverseUniverseCoverage
    assert UniverseData is UniverseUniverseData


def test_core_models_preserves_order_intent_model_import_contract():
    assert CashFlowIntent is OrderCashFlowIntent
    assert FxSpotIntent is OrderFxSpotIntent
    assert IntentRationale is OrderIntentRationale
    assert SecurityTradeIntent is OrderSecurityTradeIntent
    assert OrderIntent == OrderOrderIntent
    assert ProposalOrderIntent == OrderProposalOrderIntent


def test_core_models_preserves_diagnostics_model_import_contract():
    assert CashLadderBreach is DiagnosticsCashLadderBreach
    assert CashLadderPoint is DiagnosticsCashLadderPoint
    assert DiagnosticsData is DiagnosticsDiagnosticsData
    assert DroppedIntent is DiagnosticsDroppedIntent
    assert FundingPlanEntry is DiagnosticsFundingPlanEntry
    assert GroupConstraintEvent is DiagnosticsGroupConstraintEvent
    assert InsufficientCashEntry is DiagnosticsInsufficientCashEntry
    assert LineageData is DiagnosticsLineageData
    assert RuleResult is DiagnosticsRuleResult
    assert SuppressedIntent is DiagnosticsSuppressedIntent
    assert TaxBudgetConstraintEvent is DiagnosticsTaxBudgetConstraintEvent


def test_core_models_preserves_drift_model_import_contract():
    assert DriftAnalysis is DriftDriftAnalysis
    assert DriftBucketDetail is DriftDriftBucketDetail
    assert DriftDimensionAnalysis is DriftDriftDimensionAnalysis
    assert DriftHighlightEntry is DriftDriftHighlightEntry
    assert DriftHighlights is DriftDriftHighlights
    assert DriftReferenceModelSummary is DriftDriftReferenceModelSummary
    assert DriftUnmodeledExposure is DriftDriftUnmodeledExposure


def test_core_models_preserves_suitability_model_import_contract():
    assert SuitabilityEvidence is SuitabilitySuitabilityEvidence
    assert SuitabilityEvidenceSnapshotIds is SuitabilitySuitabilityEvidenceSnapshotIds
    assert SuitabilityIssue is SuitabilitySuitabilityIssue
    assert SuitabilityResult is SuitabilitySuitabilityResult
    assert SuitabilitySummary is SuitabilitySuitabilitySummary


def test_core_models_preserves_gate_model_import_contract():
    assert GateDecision is GateGateDecision
    assert GateDecisionSummary is GateGateDecisionSummary
    assert GateReason is GateGateReason


def test_core_models_preserves_proposal_effect_model_import_contract():
    assert Reconciliation is EffectsReconciliation
    assert TaxImpact is EffectsTaxImpact


def test_core_models_preserves_proposal_request_model_import_contract():
    assert ProposalSimulateRequest is RequestProposalSimulateRequest
    assert ProposedCashFlow is RequestProposedCashFlow
    assert ProposedTrade is RequestProposedTrade


def test_core_models_preserves_proposal_result_model_import_contract():
    assert ProposalResult is ResultProposalResult


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
    assert options.link_buy_to_same_currency_sell_dependency is None


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


def test_max_overdraft_by_ccy_accepts_non_negative_values():
    options = EngineOptions(max_overdraft_by_ccy={"USD": Decimal("10.5")})
    assert options.max_overdraft_by_ccy["USD"] == Decimal("10.5")


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


def test_snapshot_models_accept_snapshot_id():
    portfolio = PortfolioSnapshot(snapshot_id="ps_1", portfolio_id="pf", base_currency="USD")
    market = MarketDataSnapshot(
        snapshot_id="md_1",
        prices=[Price(instrument_id="EQ_1", price=Decimal("100"), currency="USD")],
        fx_rates=[],
    )
    assert portfolio.snapshot_id == "ps_1"
    assert market.snapshot_id == "md_1"


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


def test_allocation_metric_weight_serialization_preserves_decimal_precision():
    metric = AllocationMetric(
        key="EQ_1",
        weight=Decimal("0.6666666666666666666666666667"),
        value=Money(amount=Decimal("100"), currency="USD"),
    )
    payload = metric.model_dump(mode="json")
    assert payload["weight"] == "0.6666666666666666666666666667"
