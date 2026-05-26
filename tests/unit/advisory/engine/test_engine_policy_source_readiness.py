from copy import deepcopy

from src.core.proposals.policy_source_readiness import build_policy_source_readiness


def _base_evidence_bundle() -> dict:
    return {
        "context_resolution": {
            "input_mode": "stateful",
            "resolution_source": "LOTUS_CORE",
            "resolved_context": {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "as_of": "2026-05-14",
                "portfolio_snapshot_id": "core-portfolio-snapshot-001",
                "market_data_snapshot_id": "core-market-data-snapshot-001",
            },
            "advisory_policy_context": {
                "context_source": "LOTUS_CORE",
                "household_id": "HH-PB-001",
                "jurisdiction": "SG",
                "client_classification": "ACCREDITED_INVESTOR",
                "booking_center_code": "SG",
                "account_id": "ACCT-PB-001",
                "time_horizon": "5Y",
                "liquidity_need": "MEDIUM",
                "mandate_id": "MANDATE-BALANCED-001",
                "objectives": ["capital_preservation", "balanced_growth"],
                "restrictions": ["no_single_name_above_10pct"],
            },
        },
        "inputs": {
            "portfolio_snapshot": {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "base_currency": "USD",
                "positions": [{"instrument_id": "US_EQ_ETF", "quantity": "100"}],
                "cash_balances": [{"currency": "USD", "amount": "50000"}],
            },
            "market_data_snapshot": {
                "prices": [{"instrument_id": "US_EQ_ETF", "price": "100", "currency": "USD"}],
                "fx_rates": [{"pair": "USD/SGD", "rate": "1.35"}],
            },
            "shelf_entries": [
                {
                    "instrument_id": "US_EQ_ETF",
                    "eligibility": {"jurisdictions": ["SG"]},
                    "target_market": {"client_segments": ["PRIVATE_BANKING"]},
                    "complexity": "NON_COMPLEX",
                    "private_asset": False,
                    "structured_product": False,
                }
            ],
            "proposed_trades": [{"instrument_id": "US_EQ_ETF", "side": "BUY"}],
        },
        "risk_lens": {
            "source_service": "lotus-risk",
            "single_position_concentration": {"top_position_weight_current": "0.10"},
            "issuer_concentration": {"hhi_current": "1200"},
            "drawdown": {"max_drawdown_1y": "0.08"},
            "var": {"var_95_1m": "0.04"},
            "stress": {"equity_down_20": "-0.09"},
            "liquidity_risk": {"days_to_liquidate": "3"},
            "private_asset_risk": {"private_asset_weight": "0.00"},
            "climate_geopolitical_risk": {"status": "not_material"},
        },
    }


def _section(readiness: dict, key: str) -> dict:
    return next(section for section in readiness["sections"] if section["key"] == key)


def test_policy_source_readiness_marks_source_backed_policy_inputs_ready_without_policy_claims():
    readiness = build_policy_source_readiness(_base_evidence_bundle())

    assert readiness["contract_version"] == "rfc0025.policy-source-readiness.v1"
    assert readiness["capability_posture"] == (
        "SOURCE_READINESS_ONLY_POLICY_EVALUATION_NOT_IMPLEMENTED"
    )
    assert readiness["claim_policy"]["policy_evaluation"] == "NOT_IMPLEMENTED"
    assert readiness["claim_policy"]["client_ready_publication"] == "BLOCKED"
    assert _section(readiness, "core_client_profile_classification")["status"] == "READY"
    assert _section(readiness, "core_mandate_objectives_restrictions")["status"] == "READY"
    assert _section(readiness, "core_holdings_cash_market_data")["status"] == "READY"
    assert (
        _section(readiness, "core_product_eligibility_target_market_complexity")["status"]
        == "READY"
    )
    assert _section(readiness, "risk_policy_metrics")["status"] == "READY"
    assert _section(readiness, "advise_policy_evaluation_runtime")["status"] == ("PENDING_REVIEW")
    assert (
        "RFC0025_POLICY_EVALUATION_RUNTIME_NOT_IMPLEMENTED"
        in _section(readiness, "advise_policy_evaluation_runtime")["reason_codes"]
    )
    assert readiness["overall_posture"] == "PENDING_REVIEW"
    assert set(readiness["source_authority"]) == {"lotus-core", "lotus-risk", "lotus-advise"}


def test_policy_source_readiness_blocks_missing_source_owner_evidence_without_inventing_facts():
    evidence = deepcopy(_base_evidence_bundle())
    evidence["context_resolution"]["resolution_source"] = "DIRECT_REQUEST"
    evidence["context_resolution"]["advisory_policy_context"] = {"context_source": "DIRECT"}
    evidence["inputs"]["portfolio_snapshot"]["positions"] = []
    evidence["inputs"]["market_data_snapshot"]["prices"] = []
    evidence["inputs"]["shelf_entries"] = []
    evidence["risk_lens"] = None

    readiness = build_policy_source_readiness(evidence)

    assert readiness["overall_posture"] == "BLOCKED"
    client = _section(readiness, "core_client_profile_classification")
    assert client["status"] == "BLOCKED"
    assert "CORE_HOUSEHOLD_ID_NOT_PROVIDED" in client["reason_codes"]
    mandate = _section(readiness, "core_mandate_objectives_restrictions")
    assert mandate["status"] == "BLOCKED"
    assert "CORE_MANDATE_ID_NOT_PROVIDED" in mandate["reason_codes"]
    holdings = _section(readiness, "core_holdings_cash_market_data")
    assert holdings["status"] == "BLOCKED"
    assert "DIRECT_REQUEST_NOT_SOURCE_OWNER" in holdings["reason_codes"]
    assert "CORE_POSITIONS_NOT_PROVIDED" in holdings["reason_codes"]
    assert "CORE_PRICE_NOT_PROVIDED" in holdings["reason_codes"]
    product = _section(readiness, "core_product_eligibility_target_market_complexity")
    assert product["status"] == "BLOCKED"
    assert product["reason_codes"] == ["CORE_PRODUCT_SHELF_NOT_PROVIDED"]
    risk = _section(readiness, "risk_policy_metrics")
    assert risk["status"] == "BLOCKED"
    assert risk["reason_codes"] == ["RISK_OWNER_POLICY_EVIDENCE_NOT_AVAILABLE"]


def test_policy_source_readiness_keeps_partial_owner_evidence_pending_review():
    evidence = deepcopy(_base_evidence_bundle())
    evidence["context_resolution"]["advisory_policy_context"].pop("booking_center_code")
    evidence["inputs"]["shelf_entries"][0].pop("target_market")
    evidence["risk_lens"].pop("stress")

    readiness = build_policy_source_readiness(evidence)

    assert readiness["overall_posture"] == "PENDING_REVIEW"
    assert _section(readiness, "core_client_profile_classification")["status"] == ("PENDING_REVIEW")
    assert (
        "booking_center_code"
        in _section(readiness, "core_client_profile_classification")["missing_evidence"]
    )
    assert (
        _section(readiness, "core_product_eligibility_target_market_complexity")["status"]
        == "PENDING_REVIEW"
    )
    assert (
        "target_market"
        in _section(readiness, "core_product_eligibility_target_market_complexity")[
            "missing_evidence"
        ]
    )
    assert _section(readiness, "risk_policy_metrics")["status"] == "PENDING_REVIEW"
    assert "stress" in _section(readiness, "risk_policy_metrics")["missing_evidence"]
