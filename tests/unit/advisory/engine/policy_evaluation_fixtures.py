"""Shared policy-evaluation fixtures kept outside pytest collection."""

from __future__ import annotations

from typing import Any


def _base_evidence_bundle() -> dict:
    return {
        "context_resolution": {
            "as_of_date": "2026-05-26",
            "advisory_policy_context": {
                "household_id": "HH-PB-001",
                "jurisdiction": "SG",
                "client_classification": "ACCREDITED_INVESTOR",
                "booking_center_code": "SG",
                "legal_entity_code": "REFERENCE",
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
                "as_of_date": "2026-05-26",
                "positions": [{"instrument_id": "US_EQ_ETF", "quantity": "100"}],
                "cash_balances": [{"currency": "USD", "amount": "50000"}],
            },
            "market_data_snapshot": {
                "as_of_date": "2026-05-26",
                "prices": [{"instrument_id": "US_EQ_ETF", "price": "100", "currency": "USD"}],
                "fx_rates": [{"pair": "USD/SGD", "rate": "1.35"}],
            },
            "shelf_entries": [
                {
                    "instrument_id": "US_EQ_ETF",
                    "eligibility": {"jurisdictions": ["SG"]},
                    "target_market": {"client_segments": ["ACCREDITED_INVESTOR"]},
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
        "artifact": {
            "assumptions_and_limits": {
                "costs_and_fees": {"included": True},
                "tax": {"included": True},
                "execution": {"included": True},
            },
            "disclosures": {
                "product_docs": [{"instrument_id": "US_EQ_ETF", "doc_ref": "Factsheet"}],
            },
        },
        "conflict_evidence": {"material_conflict": False, "review_ref": "conflict-review-001"},
    }


def _trusted_reason(
    purpose: str,
    *,
    tenant_id: str = "tenant_sg_001",
    correlation_id: str = "corr-policy-evaluation-test",
    trace_id: str = "trace-policy-evaluation-test",
) -> dict[str, Any]:
    return {
        "purpose": purpose,
        "trusted_principal": {
            "subject": "advisor_1",
            "role": "ADVISOR",
            "tenant_id": tenant_id,
            "legal_entity_code": "REFERENCE",
            "correlation_id": correlation_id,
            "trace_id": trace_id,
            "service_identity": "lotus-gateway",
            "capability": "advisory.policy_evaluation.finalize",
        },
    }
