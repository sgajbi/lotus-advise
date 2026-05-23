from src.core.proposals.memo_source_readiness import build_memo_source_readiness


def _base_evidence_bundle() -> dict:
    return {
        "context_resolution": {
            "input_mode": "stateful",
            "resolution_source": "LOTUS_CORE",
            "used_legacy_contract": False,
            "resolved_context": {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "as_of": "2026-05-14",
                "portfolio_snapshot_id": "core-portfolio-snapshot-001",
                "market_data_snapshot_id": "core-market-data-snapshot-001",
            },
            "advisory_policy_context": {
                "context_source": "LOTUS_CORE",
                "household_id": "HH-PB-001",
                "mandate_id": "MANDATE-BALANCED-001",
                "jurisdiction": "SG",
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
                "prices": [
                    {
                        "instrument_id": "US_EQ_ETF",
                        "price": "100",
                        "currency": "USD",
                        "valid_to": "3999-12-31",
                    }
                ],
                "fx_rates": [
                    {
                        "pair": "USD/SGD",
                        "rate": "1.35",
                        "effective_to": "3999-12-31",
                    }
                ],
            },
            "shelf_entries": [
                {
                    "instrument_id": "US_EQ_ETF",
                    "eligibility": {"jurisdictions": ["SG"]},
                    "complexity": "NON_COMPLEX",
                }
            ],
            "proposed_trades": [{"instrument_id": "US_EQ_ETF", "side": "BUY"}],
            "proposed_cash_flows": [],
        },
        "engine_outputs": {
            "proposal_result": {
                "proposal_decision_summary": {"summary": "Deploy cash within mandate."},
                "proposal_alternatives": {"candidates": []},
                "gate_decision": {"gate": "CLIENT_CONSENT_REQUIRED"},
            }
        },
        "risk_lens": {
            "source_service": "lotus-risk",
            "single_position_concentration": {"top_position_weight_current": "0.10"},
            "issuer_concentration": {"hhi_current": "1200"},
        },
    }


def _section(readiness: dict, key: str) -> dict:
    return next(section for section in readiness["sections"] if section["key"] == key)


def test_memo_source_readiness_marks_source_backed_families_ready_without_memo_claims():
    readiness = build_memo_source_readiness(_base_evidence_bundle())

    assert readiness["contract_version"] == "rfc0024.memo-source-readiness.v1"
    assert readiness["capability_posture"] == (
        "SOURCE_READINESS_ONLY_MEMO_GENERATION_NOT_IMPLEMENTED"
    )
    assert readiness["claim_policy"]["memo_generation"] == "NOT_IMPLEMENTED"
    assert readiness["claim_policy"]["client_ready_publication"] == "BLOCKED"
    assert _section(readiness, "core_portfolio_holdings_cash")["status"] == "READY"
    assert _section(readiness, "core_market_prices")["status"] == "READY"
    assert _section(readiness, "core_fx_rates")["status"] == "READY"
    assert _section(readiness, "core_product_eligibility_complexity")["status"] == "READY"
    assert _section(readiness, "risk_concentration")["status"] == "READY"
    assert "lotus-core" in readiness["source_authority"]
    assert "lotus-risk" in readiness["source_authority"]


def test_memo_source_readiness_blocks_missing_owner_evidence_without_inventing_facts():
    evidence = _base_evidence_bundle()
    evidence["context_resolution"]["resolution_source"] = "DIRECT_REQUEST"
    evidence["context_resolution"]["advisory_policy_context"] = {
        "context_source": "DIRECT_REQUEST",
        "jurisdiction": "SG",
    }
    evidence["inputs"]["portfolio_snapshot"]["positions"] = []
    evidence["inputs"]["market_data_snapshot"]["prices"] = [
        {"instrument_id": "US_EQ_ETF", "price": "100", "currency": "USD"}
    ]
    evidence["inputs"]["market_data_snapshot"]["fx_rates"] = []
    evidence["inputs"]["shelf_entries"] = []
    evidence["risk_lens"] = None

    readiness = build_memo_source_readiness(evidence)

    assert readiness["overall_posture"] == "BLOCKED"
    holdings = _section(readiness, "core_portfolio_holdings_cash")
    assert holdings["status"] == "BLOCKED"
    assert "CORE_POSITIONS_NOT_PROVIDED" in holdings["reason_codes"]
    assert "DIRECT_REQUEST_NOT_SOURCE_OWNER" in holdings["reason_codes"]
    prices = _section(readiness, "core_market_prices")
    assert prices["status"] == "PENDING_REVIEW"
    assert "CORE_PRICE_OPEN_END_DATE_NOT_PROVIDED" in prices["reason_codes"]
    assert "price validity end 31-Dec-3999" in prices["missing_evidence"]
    product = _section(readiness, "core_product_eligibility_complexity")
    assert product["status"] == "BLOCKED"
    assert product["reason_codes"] == ["CORE_PRODUCT_SHELF_NOT_PROVIDED"]
    risk = _section(readiness, "risk_concentration")
    assert risk["status"] == "PENDING_REVIEW"
    assert risk["missing_evidence"] == [
        "lotus-risk source_service",
        "single_position_concentration",
        "issuer_concentration",
    ]


def test_memo_source_readiness_treats_price_and_fx_open_end_dates_as_source_contract():
    evidence = _base_evidence_bundle()
    evidence["inputs"]["market_data_snapshot"]["prices"][0].pop("valid_to")
    evidence["inputs"]["market_data_snapshot"]["fx_rates"][0]["effective_to"] = "2026-12-31"

    readiness = build_memo_source_readiness(evidence)

    assert _section(readiness, "core_market_prices")["status"] == "PENDING_REVIEW"
    assert _section(readiness, "core_market_prices")["missing_evidence"] == [
        "price validity end 31-Dec-3999"
    ]
    assert _section(readiness, "core_fx_rates")["status"] == "PENDING_REVIEW"
    assert _section(readiness, "core_fx_rates")["missing_evidence"] == [
        "FX rate validity end 31-Dec-3999"
    ]
