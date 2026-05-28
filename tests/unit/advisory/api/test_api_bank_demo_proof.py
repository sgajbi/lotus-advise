from fastapi.testclient import TestClient

from src.api.main import app
from src.core.bank_demo_proof import RFC28_CANONICAL_PORTFOLIO_ID
from tests.unit.advisory.engine.test_engine_bank_demo_proof_capture import (
    _live_runtime_payload,
    _runtime_posture,
)


def test_bank_demo_proof_contract_endpoints_expose_source_owned_truth() -> None:
    with TestClient(app) as client:
        scenario_response = client.get("/advisory/bank-demo-proof/scenario-contract")
        claim_response = client.get("/advisory/bank-demo-proof/supported-claim-register")

    assert scenario_response.status_code == 200
    assert claim_response.status_code == 200
    scenario = scenario_response.json()
    register = claim_response.json()

    assert scenario["scenario_id"] == "RFC28_BANK_DEMO_CLIENT_READY_PROOF_CANONICAL"
    assert scenario["primary_portfolio_id"] == RFC28_CANONICAL_PORTFOLIO_ID
    assert "BANK_DEMO_PROOF_PACK_CREATED" in scenario["required_evidence_markers"]

    claim_postures = {claim["claim_id"]: claim["classification"] for claim in register["claims"]}
    assert claim_postures["backend_proof_capture_repeatable"] == "IMPLEMENTATION_BACKED"
    assert (
        claim_postures["advisor_journey_backend_evidence_available"] == "BACKEND_BACKED_UI_PENDING"
    )
    assert claim_postures["advisor_use_document_proof_available"] == "BACKEND_BACKED_UI_PENDING"
    assert claim_postures["client_ready_publication_blocked"] == "UNSUPPORTED"


def test_bank_demo_proof_pack_endpoint_returns_sanitized_gateway_consumable_bundle() -> None:
    request = {
        "live_runtime_payload": _live_runtime_payload(),
        "runtime_posture": _runtime_posture().model_dump(mode="json"),
        "repository_sha": "api-sha-123",
        "service_version": "0.1.0",
        "environment": "test",
        "live_suite_result_ref": "output/live-runtime-suite/result.json",
    }

    with TestClient(app) as client:
        response = client.post(
            "/advisory/bank-demo-proof/proof-packs",
            json=request,
            headers={"X-Correlation-Id": "corr-rfc0028-api-proof"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["repository_sha"] == "api-sha-123"
    assert payload["metadata"]["correlation_id"] == "corr-rfc0028-api-proof"
    assert payload["proof_pack"]["proof_marker"] == "BANK_DEMO_PROOF_PACK_CREATED"
    assert payload["proof_pack"]["client_ready_posture"] == "CLIENT_READY_PUBLICATION_BLOCKED"
    assert "RFC0028_DOCUMENT_PROOF_SUMMARY_CREATED" in payload["proof_pack"]["evidence_markers"]
    assert payload["sanitized_runtime_summary"]["primary_portfolio_id"] == (
        RFC28_CANONICAL_PORTFOLIO_ID
    )
    assert "sha256:memo" not in repr(payload)
    assert "sha256:source-narrative" not in repr(payload)


def test_bank_demo_proof_pack_endpoint_blocks_material_drift() -> None:
    live_runtime_payload = _live_runtime_payload()
    live_runtime_payload["parity"]["proposal_policy"]["evaluation_status"] = "APPROVED"
    request = {
        "live_runtime_payload": live_runtime_payload,
        "runtime_posture": _runtime_posture().model_dump(mode="json"),
        "repository_sha": "api-sha-123",
    }

    with TestClient(app) as client:
        response = client.post("/advisory/bank-demo-proof/proof-packs", json=request)

    assert response.status_code == 409
    assert "RFC0028_BACKEND_PROOF_MATERIAL_REVIEW_BLOCKED" in response.json()["detail"]
    assert "policy_evaluation='APPROVED'" in response.json()["detail"]


def test_bank_demo_proof_openapi_documents_gateway_contract_and_error_model() -> None:
    operation = app.openapi()["paths"]["/advisory/bank-demo-proof/proof-packs"]["post"]

    assert operation["tags"] == ["Bank Demo Proof"]
    assert "Gateway and Workbench cannot promote stale" in operation["description"]
    assert "409" in operation["responses"]
    assert "422" in operation["responses"]
