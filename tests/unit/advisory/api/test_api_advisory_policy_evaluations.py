from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient

from src.api.main import app
from src.core.policy_packs import (
    get_policy_pack_version,
    reset_policy_evaluation_store_for_tests,
    reset_policy_pack_catalog_for_tests,
)


def setup_function() -> None:
    reset_policy_pack_catalog_for_tests()
    reset_policy_evaluation_store_for_tests()


def _base_evidence_bundle() -> dict:
    return {
        "context_resolution": {
            "advisory_policy_context": {
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
            }
        },
        "inputs": {
            "portfolio_snapshot": {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
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


def _create_payload(evidence: dict | None = None) -> dict:
    return {
        "policy_pack_id": "GLOBAL_PRIVATE_BANKING_BASELINE",
        "policy_version": "2026.05",
        "created_by": "advisor_1",
        "evidence_bundle": evidence or _base_evidence_bundle(),
        "reason": {"purpose": "advisor suitability review"},
    }


def _activate_sg_pack(client: TestClient) -> None:
    content_hash = get_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
    ).policy_pack.content_hash
    validated = client.post(
        "/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05/validate",
        json={"requested_by": "policy_steward_1", "reason": {"purpose": "api test"}},
        headers={"Idempotency-Key": "api-policy-eval-validate-sg"},
    )
    assert validated.status_code == 200
    activated = client.post(
        "/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05/activate",
        json={
            "activated_by": "policy_checker_1",
            "source_content_hash": content_hash,
            "reason": {"purpose": "api test"},
        },
        headers={"Idempotency-Key": "api-policy-eval-activate-sg"},
    )
    assert activated.status_code == 200


def _sg_pending_payload() -> dict:
    evidence = _base_evidence_bundle()
    evidence["inputs"]["shelf_entries"][0]["instrument_id"] = "SG_STRUCTURED_NOTE"
    evidence["inputs"]["shelf_entries"][0]["complexity"] = "COMPLEX"
    evidence["inputs"]["shelf_entries"][0]["structured_product"] = True
    evidence["inputs"]["proposed_trades"][0]["instrument_id"] = "SG_STRUCTURED_NOTE"
    evidence["artifact"]["disclosures"]["product_docs"] = [
        {"instrument_id": "SG_STRUCTURED_NOTE", "doc_ref": "Term sheet"}
    ]
    payload = _create_payload(evidence)
    payload["policy_pack_id"] = "SG_PRIVATE_BANKING_REFERENCE"
    return payload


def test_policy_evaluation_api_finalizes_reads_replays_and_records_events() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/advisory/proposals/pp_policy_api_001/versions/ppv_policy_api_001/policy-evaluations",
            json=_create_payload(),
            headers={"Idempotency-Key": "api-policy-eval-create-001"},
        )
        assert created.status_code == 200
        created_body = created.json()
        evaluation_id = created_body["record"]["evaluation_id"]

        replayed = client.post(
            "/advisory/proposals/pp_policy_api_001/versions/ppv_policy_api_001/policy-evaluations",
            json=_create_payload(),
            headers={"Idempotency-Key": "api-policy-eval-create-001"},
        )
        assert replayed.status_code == 200
        assert replayed.json()["replayed"] is True

        drift = client.post(
            "/advisory/proposals/pp_policy_api_001/versions/ppv_policy_api_001/policy-evaluations",
            json={**_create_payload(), "reason": {"purpose": "changed"}},
            headers={"Idempotency-Key": "api-policy-eval-create-001"},
        )
        assert drift.status_code == 409

        read = client.get(f"/advisory/policy-evaluations/{evaluation_id}")
        assert read.status_code == 200
        read_body = read.json()
        assert read_body["evaluation_hash"].startswith("sha256:")
        assert read_body["evaluation_json"]["supportability"]["policy_evaluation_api"] == (
            "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API"
        )
        assert read_body["evaluation_json"]["supportability"]["gateway_supported"] is False

        replay = client.post(
            f"/advisory/policy-evaluations/{evaluation_id}/replay",
            json={"evidence_bundle": _base_evidence_bundle()},
        )
        assert replay.status_code == 200
        assert replay.json()["hash_comparison"]["evaluation_hash_matches"] is True

        changed_evidence = deepcopy(_base_evidence_bundle())
        changed_evidence["inputs"]["market_data_snapshot"]["fx_rates"][0]["rate"] = "1.36"
        changed = client.post(
            f"/advisory/policy-evaluations/{evaluation_id}/replay",
            json={"evidence_bundle": changed_evidence},
        )
        assert changed.status_code == 200
        assert changed.json()["hash_comparison"]["source_evidence_hash_matches"] is False

        review = client.post(
            f"/advisory/policy-evaluations/{evaluation_id}/events",
            json={
                "event_type": "POLICY_EVALUATION_REVIEW_RECORDED",
                "actor_id": "compliance_1",
                "reason": {"review_action": "REQUEST_MORE_EVIDENCE"},
            },
            headers={"Idempotency-Key": "api-policy-eval-review-001"},
        )
        assert review.status_code == 200
        assert review.json()["event_type"] == "POLICY_EVALUATION_REVIEW_RECORDED"

        lineage = client.get(f"/advisory/policy-evaluations/{evaluation_id}/lineage")
        assert lineage.status_code == 200
        lineage_body = lineage.json()
        assert [event["event_type"] for event in lineage_body["audit_events"]] == [
            "POLICY_EVALUATION_FINALIZED",
            "POLICY_EVALUATION_REVIEW_RECORDED",
        ]
        assert lineage_body["lineage_posture"]["client_ready_publication"] == "BLOCKED"

        sign_off = client.get(f"/advisory/policy-evaluations/{evaluation_id}/sign-off-package")
        assert sign_off.status_code == 200
        sign_off_body = sign_off.json()
        assert sign_off_body["evaluation"]["evaluation_id"] == evaluation_id
        assert sign_off_body["package_posture"]["report_render_archive_realization"] == (
            "NOT_IMPLEMENTED"
        )


def test_policy_review_queue_filters_records_that_need_policy_review() -> None:
    with TestClient(app) as client:
        _activate_sg_pack(client)
        created = client.post(
            "/advisory/proposals/pp_policy_queue_001/versions/ppv_policy_queue_001/policy-evaluations",
            json=_sg_pending_payload(),
            headers={"Idempotency-Key": "api-policy-eval-queue-001"},
        )
        assert created.status_code == 200
        evaluation_id = created.json()["record"]["evaluation_id"]

        queue = client.get("/advisory/policy-evaluations/review-queue")
        assert queue.status_code == 200
        queue_body = queue.json()
        assert [item["evaluation_id"] for item in queue_body["items"]] == [evaluation_id]
        assert queue_body["items"][0]["evaluation_status"] == "PENDING_REVIEW"
        assert queue_body["queue_posture"]["workbench_supported"] is False

        ready_queue = client.get(
            "/advisory/policy-evaluations/review-queue",
            params={"evaluation_status": "READY"},
        )
        assert ready_queue.status_code == 200
        assert ready_queue.json()["items"] == []


def test_policy_evaluation_openapi_registers_certified_advise_routes() -> None:
    app.openapi_schema = None
    openapi = app.openapi()
    paths = openapi["paths"]

    create_path = (
        "/advisory/proposals/{proposal_id}/versions/{proposal_version_id}/policy-evaluations"
    )
    assert paths[create_path]["post"]["tags"] == ["Advisory Policy Evaluation"]
    assert (
        paths[create_path]["post"]["parameters"][2]["description"]
        == "Required idempotency key for replay-safe policy evaluation finalization."
    )
    assert "/advisory/policy-evaluations/review-queue" in paths
    assert "/advisory/policy-evaluations/{evaluation_id}/events" in paths
    assert "/advisory/policy-evaluations/{evaluation_id}/lineage" in paths
    assert "/advisory/policy-evaluations/{evaluation_id}/sign-off-package" in paths
