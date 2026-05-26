from fastapi.testclient import TestClient

from src.api.main import app
from src.core.policy_packs import reset_policy_pack_catalog_for_tests


def setup_function() -> None:
    reset_policy_pack_catalog_for_tests()


def test_policy_pack_catalog_routes_list_detail_validate_activate_and_preserve_boundaries() -> None:
    with TestClient(app) as client:
        listed = client.get("/advisory/policy-packs")
        assert listed.status_code == 200
        listed_body = listed.json()
        policy_pack_ids = {item["policy_pack_id"] for item in listed_body["items"]}
        assert policy_pack_ids == {
            "GLOBAL_PRIVATE_BANKING_BASELINE",
            "SG_PRIVATE_BANKING_REFERENCE",
        }
        assert listed_body["catalog_posture"]["policy_evaluation"] == "NOT_IMPLEMENTED"
        assert listed_body["catalog_posture"]["client_ready_publication"] == "BLOCKED"

        detail = client.get("/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05")
        assert detail.status_code == 200
        detail_body = detail.json()
        content_hash = detail_body["policy_pack"]["content_hash"]
        assert detail_body["policy_pack"]["activation_state"] == "DRAFT"
        assert detail_body["policy_pack"]["reference_posture"] == (
            "REFERENCE_EXAMPLE_NOT_LEGAL_ADVICE"
        )
        assert detail_body["supportability"]["policy_evaluation"] == "NOT_IMPLEMENTED"
        assert detail_body["supportability"]["gateway_supported"] is False
        assert detail_body["supportability"]["workbench_supported"] is False

        validation = client.post(
            "/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05/validate",
            json={
                "requested_by": "policy_steward_1",
                "reason": {"purpose": "pre-activation validation"},
            },
            headers={"Idempotency-Key": "api-validate-sg-reference"},
        )
        assert validation.status_code == 200
        validation_body = validation.json()
        assert validation_body["validation_status"] == "READY"
        assert validation_body["validation_event"]["content_hash"] == content_hash

        maker_checker_block = client.post(
            "/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05/activate",
            json={
                "activated_by": "policy_steward_1",
                "source_content_hash": content_hash,
                "reason": {"purpose": "same actor"},
            },
            headers={"Idempotency-Key": "api-activate-same-actor"},
        )
        assert maker_checker_block.status_code == 422
        assert maker_checker_block.json()["detail"] == (
            "POLICY_PACK_MAKER_CHECKER_REQUIRES_DIFFERENT_ACTOR"
        )

        activation = client.post(
            "/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05/activate",
            json={
                "activated_by": "policy_checker_1",
                "source_content_hash": content_hash,
                "reason": {"purpose": "activate reference pack"},
            },
            headers={"Idempotency-Key": "api-activate-sg-reference"},
        )
        assert activation.status_code == 200
        activation_body = activation.json()
        assert activation_body["policy_pack"]["activation_state"] == "ACTIVE"
        assert activation_body["activation_event"]["content_hash"] == content_hash
        assert activation_body["activation_event"]["reason"]["validated_by"] == "policy_steward_1"

        active_detail = client.get(
            "/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05"
        )
        assert active_detail.status_code == 200
        active_body = active_detail.json()
        assert active_body["policy_pack"]["activation_state"] == "ACTIVE"
        assert [event["event_type"] for event in active_body["audit_events"]] == [
            "POLICY_PACK_VALIDATED",
            "POLICY_PACK_ACTIVATED",
        ]


def test_policy_pack_catalog_openapi_documents_canonical_routes_without_evaluation_route() -> None:
    openapi = app.openapi()
    paths = openapi["paths"]

    assert "/advisory/policy-packs" in paths
    assert "/advisory/policy-packs/{policy_pack_id}/versions/{policy_version}/validate" in paths
    assert "/advisory/policy-packs/{policy_pack_id}/versions/{policy_version}/activate" in paths
    assert "/advisory/proposals/{proposal_id}/versions/{version_id}/policy-evaluations" not in paths
    assert paths["/advisory/policy-packs"]["get"]["tags"] == ["Advisory Policy Packs"]
