import json
import os
from decimal import Decimal

import pytest

from src.core.advisory_engine import run_proposal_simulation
from src.core.models import EngineOptions, MarketDataSnapshot, PortfolioSnapshot, ShelfEntry


def _load_golden(path):
    with open(path, "r") as file:
        return json.loads(file.read(), parse_float=Decimal)


@pytest.mark.parametrize(
    "filename",
    [
        "scenario_14A_advisory_manual_trade_cashflow.json",
        "scenario_14B_auto_funding_single_ccy.json",
        "scenario_14B_partial_funding.json",
        "scenario_14B_missing_fx_blocked.json",
        "scenario_14C_drift_asset_class.json",
        "scenario_14C_drift_instrument.json",
        "scenario_14D_single_position_resolved.json",
        "scenario_14D_new_issuer_breach.json",
        "scenario_14D_sell_only_violation.json",
    ],
)
def test_golden_advisory_proposal_scenarios(filename):
    path = os.path.join(os.path.dirname(__file__), "../golden_data", filename)
    data = _load_golden(path)

    inputs = data["proposal_inputs"]
    expected = data["expected_proposal_output"]

    result = run_proposal_simulation(
        portfolio=PortfolioSnapshot(**inputs["portfolio_snapshot"]),
        market_data=MarketDataSnapshot(**inputs["market_data_snapshot"]),
        shelf=[ShelfEntry(**entry) for entry in inputs["shelf_entries"]],
        options=EngineOptions(**inputs["options"]),
        proposed_cash_flows=inputs["proposed_cash_flows"],
        proposed_trades=inputs["proposed_trades"],
        reference_model=inputs.get("reference_model"),
        request_hash="golden_proposal_test",
    )

    assert result.status == expected["status"]
    assert [intent.intent_type for intent in result.intents] == [
        intent["intent_type"] for intent in expected["intents"]
    ]

    for idx, expected_intent in enumerate(expected["intents"]):
        actual = result.intents[idx]
        if "side" in expected_intent:
            assert actual.side == expected_intent["side"]
        if "instrument_id" in expected_intent:
            assert actual.instrument_id == expected_intent["instrument_id"]
        if "pair" in expected_intent:
            assert actual.pair == expected_intent["pair"]
        if "dependencies" in expected_intent:
            assert actual.dependencies == expected_intent["dependencies"]

    if "missing_fx_pairs" in expected:
        assert sorted(result.diagnostics.missing_fx_pairs) == sorted(expected["missing_fx_pairs"])

    if "funding_plan" in expected:
        assert len(result.diagnostics.funding_plan) == len(expected["funding_plan"])

    if "insufficient_cash" in expected:
        assert len(result.diagnostics.insufficient_cash) == len(expected["insufficient_cash"])

    expected_drift = expected.get("drift_analysis")
    if expected_drift is not None:
        assert result.drift_analysis is not None
        assert result.drift_analysis.asset_class.drift_total_before == Decimal(
            expected_drift["asset_class"]["drift_total_before"]
        )
        assert result.drift_analysis.asset_class.drift_total_after == Decimal(
            expected_drift["asset_class"]["drift_total_after"]
        )
        assert result.drift_analysis.asset_class.drift_total_delta == Decimal(
            expected_drift["asset_class"]["drift_total_delta"]
        )
        assert [
            item.bucket for item in result.drift_analysis.asset_class.top_contributors_before
        ] == [item["bucket"] for item in expected_drift["asset_class"]["top_contributors_before"]]
        if "instrument" in expected_drift:
            assert result.drift_analysis.instrument is not None
            assert result.drift_analysis.instrument.drift_total_before == Decimal(
                expected_drift["instrument"]["drift_total_before"]
            )
            assert result.drift_analysis.instrument.drift_total_after == Decimal(
                expected_drift["instrument"]["drift_total_after"]
            )
            assert result.drift_analysis.instrument.drift_total_delta == Decimal(
                expected_drift["instrument"]["drift_total_delta"]
            )
            assert [
                item.bucket for item in result.drift_analysis.instrument.top_contributors_before
            ] == [
                item["bucket"] for item in expected_drift["instrument"]["top_contributors_before"]
            ]

    expected_suitability = expected.get("suitability")
    if expected_suitability is not None:
        assert result.suitability is not None
        assert result.suitability.summary.new_count == expected_suitability["summary"]["new_count"]
        assert (
            result.suitability.summary.resolved_count
            == expected_suitability["summary"]["resolved_count"]
        )
        assert (
            result.suitability.summary.persistent_count
            == expected_suitability["summary"]["persistent_count"]
        )
        assert (
            result.suitability.summary.highest_severity_new
            == expected_suitability["summary"]["highest_severity_new"]
        )
        assert result.suitability.recommended_gate == expected_suitability["recommended_gate"]
        assert [item.issue_key for item in result.suitability.issues] == [
            item["issue_key"] for item in expected_suitability["issues"]
        ]
        assert [item.status_change for item in result.suitability.issues] == [
            item["status_change"] for item in expected_suitability["issues"]
        ]
