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
    assert claim_postures["ai_policy_cockpit_proof_integrated"] == "IMPLEMENTATION_BACKED"
    assert claim_postures["commercial_rfp_security_material_available"] == "IMPLEMENTATION_BACKED"
    assert claim_postures["rfp_security_package_pending"] == "UNSUPPORTED"
    assert claim_postures["client_ready_publication_blocked"] == "UNSUPPORTED"
    scenario_panels = {
        panel for step in scenario["steps"] for panel in step["required_workbench_panels"]
    }
    assert "advisory.advisor_cockpit" in scenario_panels
    assert "advisor_cockpit" not in scenario_panels


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
    assert (
        "RFC0028_JOURNEY_INTEGRATION_PROOF_CREATED" in (payload["proof_pack"]["evidence_markers"])
    )
    assert "RFC0028_COMMERCIAL_MATERIAL_PACK_CREATED" in (payload["proof_pack"]["evidence_markers"])
    assert (
        "RFC0028_RUNTIME_SECURITY_POSTURE_HARDENED" in (payload["proof_pack"]["evidence_markers"])
    )
    assert payload["commercial_material_pack"]["publication_posture"] == (
        "CUSTOMER_CONSUMABLE_WITH_BOUNDARIES"
    )
    commercial_material_ids = {
        material["material_id"] for material in payload["commercial_material_pack"]["materials"]
    }
    assert "rfp_response_pack" in commercial_material_ids
    assert "security_posture_pack" in commercial_material_ids
    assert "client_ready_publication" in payload["commercial_material_pack"]["blocked_claims"]
    assert (
        payload["journey_integration_proof_summary"]["policy_evidence"]["client_ready_publication"]
        == "BLOCKED"
    )
    ai_rows = {
        row["evidence_family"]: row
        for row in payload["journey_integration_proof_summary"]["ai_model_risk_controls"]
    }
    assert ai_rows["POLICY_EVIDENCE"]["raw_source_evidence_included"] is False
    assert ai_rows["ADVISORY_COPILOT"]["proof_posture"] == "NOT_PROBED"
    assert payload["sanitized_runtime_summary"]["primary_portfolio_id"] == (
        RFC28_CANONICAL_PORTFOLIO_ID
    )
    assert "latency_ms" in payload["runtime_posture"]["endpoints"][0]
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


def test_bank_demo_proof_pack_endpoint_rejects_malformed_source_evidence_as_422() -> None:
    live_runtime_payload = _live_runtime_payload()
    del live_runtime_payload["parity"]["proposal_policy"]["policy_pack_id"]
    request = {
        "live_runtime_payload": live_runtime_payload,
        "runtime_posture": _runtime_posture().model_dump(mode="json"),
        "repository_sha": "api-sha-123",
    }

    with TestClient(app) as client:
        response = client.post("/advisory/bank-demo-proof/proof-packs", json=request)

    assert response.status_code == 422
    assert "RFC0028_INTEGRATION_PROOF_FIELD_MISSING" in response.json()["detail"]
    assert "policy_pack_id" in response.json()["detail"]


def test_bank_demo_proof_pack_endpoint_redacts_sensitive_source_evidence_errors() -> None:
    live_runtime_payload = _live_runtime_payload()
    live_runtime_payload["parity"]["proposal_policy"]["evaluation_status"] = "token=should-not-leak"
    request = {
        "live_runtime_payload": live_runtime_payload,
        "runtime_posture": _runtime_posture().model_dump(mode="json"),
        "repository_sha": "api-sha-123",
    }

    with TestClient(app) as client:
        response = client.post("/advisory/bank-demo-proof/proof-packs", json=request)

    assert response.status_code == 422
    detail = repr(response.json()["detail"])
    assert "RFC0028_PROOF_PACK_VALIDATION_FAILED" in detail
    assert "token" not in detail
    assert "should-not-leak" not in detail


def test_bank_demo_proof_pack_endpoint_rejects_sensitive_artifact_refs_as_request_shape() -> None:
    request = {
        "live_runtime_payload": _live_runtime_payload(),
        "runtime_posture": _runtime_posture().model_dump(mode="json"),
        "repository_sha": "api-sha-123",
        "live_suite_result_ref": "output/live-runtime-suite/result.json?token=should-not-leak",
        "output_ref_prefix": "../output/rfc0028/backend-proof",
    }

    with TestClient(app) as client:
        response = client.post("/advisory/bank-demo-proof/proof-packs", json=request)

    assert response.status_code == 422
    detail = repr(response.json()["detail"])
    assert "live_suite_result_ref must not include URL" in detail
    assert "output_ref_prefix cannot contain parent-directory traversal" in detail
    assert "should-not-leak" not in detail


def test_bank_demo_proof_pack_endpoint_bounds_metadata_and_correlation_header() -> None:
    request = {
        "live_runtime_payload": _live_runtime_payload(),
        "runtime_posture": _runtime_posture().model_dump(mode="json"),
        "repository_sha": "x" * 161,
        "service_version": "0.1.0",
        "environment": "test",
    }
    sensitive_environment = {
        **request,
        "repository_sha": "api-sha-123",
        "environment": "prod-token",
    }
    oversized_payload = {
        **request,
        "repository_sha": "api-sha-123",
        "live_runtime_payload": {f"top_level_{index}": {} for index in range(17)},
    }

    with TestClient(app) as client:
        long_sha = client.post("/advisory/bank-demo-proof/proof-packs", json=request)
        sensitive_metadata = client.post(
            "/advisory/bank-demo-proof/proof-packs",
            json=sensitive_environment,
        )
        long_correlation = client.post(
            "/advisory/bank-demo-proof/proof-packs",
            json={**request, "repository_sha": "api-sha-123"},
            headers={"X-Correlation-Id": "x" * 129},
        )
        long_live_payload = client.post(
            "/advisory/bank-demo-proof/proof-packs",
            json=oversized_payload,
        )

    assert long_sha.status_code == 422
    assert sensitive_metadata.status_code == 422
    assert "environment cannot contain sensitive material" in repr(sensitive_metadata.json())
    assert long_correlation.status_code == 422
    assert long_live_payload.status_code == 422


def test_bank_demo_proof_openapi_documents_gateway_contract_and_error_model() -> None:
    operation = app.openapi()["paths"]["/advisory/bank-demo-proof/proof-packs"]["post"]

    assert operation["tags"] == ["Bank Demo Proof"]
    assert "Gateway and Workbench cannot promote stale" in operation["description"]
    assert "409" in operation["responses"]
    assert "422" in operation["responses"]
    assert "source evidence validation failed" in operation["responses"]["422"]["description"]
    assert (
        "RFC0028_BACKEND_PROOF_MATERIAL_REVIEW_BLOCKED"
        in (operation["responses"]["409"]["content"]["application/json"]["example"]["detail"])
    )
    assert (
        "RFC0028_INTEGRATION_PROOF_FIELD_MISSING"
        in (operation["responses"]["422"]["content"]["application/json"]["example"]["detail"])
    )
    runtime_endpoint_schema = app.openapi()["components"]["schemas"]["RuntimeEndpointEvidence"]
    assert "latency_ms" in runtime_endpoint_schema["properties"]
    assert runtime_endpoint_schema["properties"]["endpoint"]["maxLength"] == 160
    runtime_posture_schema = app.openapi()["components"]["schemas"]["BackendRuntimePosture"]
    assert runtime_posture_schema["properties"]["base_url"]["maxLength"] == 512
    assert runtime_posture_schema["properties"]["endpoints"]["maxItems"] == 32
    request_schema = app.openapi()["components"]["schemas"]["BankDemoProofCaptureRequest"]
    assert "query strings" in request_schema["properties"]["output_ref_prefix"]["description"]
    assert request_schema["properties"]["live_runtime_payload"]["maxProperties"] == 16
