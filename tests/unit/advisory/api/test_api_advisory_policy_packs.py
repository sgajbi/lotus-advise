from fastapi.testclient import TestClient

from src.api.main import app
from src.api.proposals.policy_control_principal import (
    POLICY_CHECKER_ROLE,
    POLICY_CONTROL_ACTOR_MISMATCH,
    POLICY_CONTROL_PRINCIPAL_REQUIRED,
    POLICY_CONTROL_ROLE_NOT_AUTHORIZED,
    POLICY_PACK_ACTIVATE_CAPABILITY,
    POLICY_PACK_VALIDATE_CAPABILITY,
    POLICY_STEWARD_ROLE,
)
from src.core.policy_packs import (
    reset_policy_evaluation_store_for_tests,
    reset_policy_pack_catalog_for_tests,
)


def setup_function() -> None:
    reset_policy_pack_catalog_for_tests()
    reset_policy_evaluation_store_for_tests()


def _policy_headers(
    *,
    actor_id: str,
    role: str,
    capability: str,
    idempotency_key: str | None = None,
    legal_entity_code: str = "REFERENCE",
) -> dict[str, str]:
    headers = {
        "X-Actor-Id": actor_id,
        "X-Role": role,
        "X-Tenant-Id": "tenant_sg_001",
        "X-Legal-Entity-Code": legal_entity_code,
        "X-Correlation-Id": f"corr-{actor_id}",
        "X-Service-Identity": "lotus-gateway",
        "X-Capabilities": capability,
    }
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    return headers


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
        assert listed_body["catalog_posture"]["policy_evaluation"] == (
            "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API"
        )
        assert listed_body["catalog_posture"]["client_ready_publication"] == "BLOCKED"

        detail = client.get("/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05")
        assert detail.status_code == 200
        detail_body = detail.json()
        content_hash = detail_body["policy_pack"]["content_hash"]
        assert detail_body["policy_pack"]["activation_state"] == "DRAFT"
        assert detail_body["policy_pack"]["reference_posture"] == (
            "REFERENCE_EXAMPLE_NOT_LEGAL_ADVICE"
        )
        assert detail_body["supportability"]["policy_evaluation"] == (
            "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API"
        )
        assert detail_body["supportability"]["gateway_supported"] is True
        assert detail_body["supportability"]["gateway_support"] == (
            "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_BFF"
        )
        assert detail_body["supportability"]["workbench_supported"] is True
        assert detail_body["supportability"]["workbench_support"] == (
            "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_ONLY_UI"
        )
        assert detail_body["supportability"]["active_data_product_promotion"] == (
            "SUPPORTED_BY_RFC0025_SLICE16_FINAL_CLOSURE"
        )

        validation = client.post(
            "/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05/validate",
            json={
                "requested_by": "policy_steward_1",
                "reason": {"purpose": "pre-activation validation"},
            },
            headers=_policy_headers(
                actor_id="policy_steward_1",
                role=POLICY_STEWARD_ROLE,
                capability=POLICY_PACK_VALIDATE_CAPABILITY,
                idempotency_key="api-validate-sg-reference",
            ),
        )
        assert validation.status_code == 200
        validation_body = validation.json()
        assert validation_body["validation_status"] == "READY"
        assert validation_body["validation_event"]["content_hash"] == content_hash

        hash_mismatch = client.post(
            "/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05/activate",
            json={
                "activated_by": "policy_checker_1",
                "source_content_hash": "sha256:wrong-policy-pack-content",
                "reason": {"purpose": "activate with stale hash"},
            },
            headers=_policy_headers(
                actor_id="policy_checker_1",
                role=POLICY_CHECKER_ROLE,
                capability=POLICY_PACK_ACTIVATE_CAPABILITY,
                idempotency_key="api-activate-hash-mismatch",
            ),
        )
        assert hash_mismatch.status_code == 422
        assert hash_mismatch.json()["detail"] == "POLICY_PACK_CONTENT_HASH_MISMATCH"

        maker_checker_block = client.post(
            "/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05/activate",
            json={
                "activated_by": "policy_steward_1",
                "source_content_hash": content_hash,
                "reason": {"purpose": "same actor"},
            },
            headers=_policy_headers(
                actor_id="policy_steward_1",
                role=POLICY_CHECKER_ROLE,
                capability=POLICY_PACK_ACTIVATE_CAPABILITY,
                idempotency_key="api-activate-same-actor",
            ),
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
            headers=_policy_headers(
                actor_id="policy_checker_1",
                role=POLICY_CHECKER_ROLE,
                capability=POLICY_PACK_ACTIVATE_CAPABILITY,
                idempotency_key="api-activate-sg-reference",
            ),
        )
        assert activation.status_code == 200
        activation_body = activation.json()
        assert activation_body["policy_pack"]["activation_state"] == "ACTIVE"
        assert activation_body["activation_event"]["content_hash"] == content_hash
        assert activation_body["activation_event"]["reason"]["validated_by"] == "policy_steward_1"

        activation_replay = client.post(
            "/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05/activate",
            json={
                "activated_by": "policy_checker_1",
                "source_content_hash": content_hash,
                "reason": {"purpose": "activate reference pack"},
            },
            headers=_policy_headers(
                actor_id="policy_checker_1",
                role=POLICY_CHECKER_ROLE,
                capability=POLICY_PACK_ACTIVATE_CAPABILITY,
                idempotency_key="api-activate-sg-reference",
            ),
        )
        assert activation_replay.status_code == 200
        activation_replay_body = activation_replay.json()
        assert activation_replay_body["replayed"] is True
        assert (
            activation_replay_body["activation_event"]["event_id"]
            == (activation_body["activation_event"]["event_id"])
        )

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


def test_policy_pack_control_routes_require_trusted_principal_and_reject_spoofing() -> None:
    with TestClient(app) as client:
        missing_auth = client.post(
            "/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05/validate",
            json={"requested_by": "policy_steward_1"},
            headers={"Idempotency-Key": "api-policy-pack-missing-auth"},
        )
        assert missing_auth.status_code == 401
        assert missing_auth.json()["detail"] == POLICY_CONTROL_PRINCIPAL_REQUIRED

        wrong_role = client.post(
            "/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05/validate",
            json={"requested_by": "policy_steward_1"},
            headers=_policy_headers(
                actor_id="policy_steward_1",
                role=POLICY_CHECKER_ROLE,
                capability=POLICY_PACK_VALIDATE_CAPABILITY,
                idempotency_key="api-policy-pack-wrong-role",
            ),
        )
        assert wrong_role.status_code == 403
        assert wrong_role.json()["detail"] == POLICY_CONTROL_ROLE_NOT_AUTHORIZED

        spoofed_actor = client.post(
            "/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05/validate",
            json={"requested_by": "impersonated_policy_steward"},
            headers=_policy_headers(
                actor_id="policy_steward_1",
                role=POLICY_STEWARD_ROLE,
                capability=POLICY_PACK_VALIDATE_CAPABILITY,
                idempotency_key="api-policy-pack-spoofed-actor",
            ),
        )
        assert spoofed_actor.status_code == 403
        assert spoofed_actor.json()["detail"] == POLICY_CONTROL_ACTOR_MISMATCH


def test_policy_pack_catalog_openapi_documents_canonical_routes_with_evaluation_routes() -> None:
    app.openapi_schema = None
    openapi = app.openapi()
    paths = openapi["paths"]

    assert "/advisory/policy-packs" in paths
    assert "/advisory/policy-packs/{policy_pack_id}/versions/{policy_version}/validate" in paths
    assert "/advisory/policy-packs/{policy_pack_id}/versions/{policy_version}/activate" in paths
    assert (
        "/advisory/proposals/{proposal_id}/versions/{proposal_version_id}/policy-evaluations"
        in paths
    )
    assert "/advisory/policy-evaluations/{evaluation_id}/replay" in paths
    assert paths["/advisory/policy-packs"]["get"]["tags"] == ["Advisory Policy Packs"]
