from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

import src.api.proposals.router as proposals_router
import src.core.advisor_cockpit.service as cockpit_service
from src.api.main import app
from src.api.proposals.router import reset_proposal_workflow_service_for_tests
from src.core.policy_packs.models import PolicyEvaluationRecord
from src.core.proposals.models import ProposalMemoRecord, ProposalRecord
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository

NOW = datetime(2026, 5, 27, 8, 0, tzinfo=UTC)


def setup_function() -> None:
    reset_proposal_workflow_service_for_tests()


@pytest.fixture()
def cockpit_repository(monkeypatch: pytest.MonkeyPatch) -> InMemoryProposalRepository:
    repository = InMemoryProposalRepository()
    repository.create_proposal(
        ProposalRecord(
            proposal_id="proposal_sg_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            created_by="advisor_sg_001",
            created_at=NOW,
            last_event_at=NOW,
            current_state="COMPLIANCE_REVIEW",
            current_version_no=1,
            title="Singapore global balanced proposal",
        )
    )
    repository.create_memo(
        ProposalMemoRecord(
            memo_id="memo_sg_001",
            proposal_id="proposal_sg_001",
            proposal_version_no=1,
            memo_version="advisory-proposal-memo-evidence-pack.v1",
            memo_status="BLOCKED",
            lifecycle_status="FINALIZED",
            created_by="advisor_sg_001",
            created_at=NOW,
            source_input_hash="sha256:memo-source",
            memo_hash="sha256:memo",
            memo_json={"memo_id": "memo_sg_001"},
        )
    )
    monkeypatch.setattr(proposals_router.runtime, "build_repository", lambda: repository)
    monkeypatch.setattr(
        cockpit_service,
        "list_policy_evaluation_records",
        lambda **_: [
            PolicyEvaluationRecord(
                evaluation_id="policy_eval_sg_001",
                proposal_id="proposal_sg_001",
                proposal_version_id="ppv_sg_001",
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
                policy_version="2026.05",
                generated_at="2026-05-27T08:00:00+00:00",
                created_by="advisor_sg_001",
                evaluation_status="PENDING_REVIEW",
                policy_content_hash="sha256:policy-content",
                source_evidence_hash="sha256:source-evidence",
                evaluation_hash="sha256:policy-evaluation",
                evaluation_json={"evaluation_status": "PENDING_REVIEW"},
            )
        ],
    )
    return repository


def test_advisor_cockpit_api_lists_actions_and_snapshot(
    cockpit_repository: InMemoryProposalRepository,
) -> None:
    _ = cockpit_repository
    with TestClient(app) as client:
        actions = client.get(
            "/advisory/cockpit/actions",
            params={"portfolio_id": "PB_SG_GLOBAL_BAL_001", "advisor_id": "advisor_sg_001"},
            headers={"X-Correlation-ID": "corr-cockpit-api"},
        )
        snapshot = client.get(
            "/advisory/cockpit/snapshot",
            params={"portfolio_id": "PB_SG_GLOBAL_BAL_001", "advisor_id": "advisor_sg_001"},
        )
        supportability_response = client.get(
            "/advisory/cockpit/supportability",
            params={"portfolio_id": "PB_SG_GLOBAL_BAL_001", "advisor_id": "advisor_sg_001"},
        )

    assert actions.status_code == 200
    action_payload = actions.json()
    assert action_payload["total_count"] == 3
    assert action_payload["items"][0]["action_family"] == "POLICY_REVIEW_REQUIRED"
    assert action_payload["items"][0]["correlation_id"] == "corr-cockpit-api"
    assert snapshot.status_code == 200
    supportability = snapshot.json()["supportability"]
    assert supportability["gateway_posture"] == "SUPPORTED_BY_LOTUS_GATEWAY_RFC0026"
    assert supportability["workbench_posture"] == "CANONICAL_WORKBENCH_PROOF_PASSED_RFC0026"
    assert supportability["data_product_posture"] == "ACTIVE_ADVISOR_COCKPIT_PRODUCTS_RFC0026"
    assert supportability_response.status_code == 200
    assert supportability_response.json()["posture"] == (
        "ADVISE_GATEWAY_WORKBENCH_CANONICAL_PROOF_SUPPORTED"
    )


def test_advisor_cockpit_api_acknowledgement_is_replay_safe(
    cockpit_repository: InMemoryProposalRepository,
) -> None:
    _ = cockpit_repository
    with TestClient(app) as client:
        actions = client.get(
            "/advisory/cockpit/actions",
            params={"portfolio_id": "PB_SG_GLOBAL_BAL_001", "advisor_id": "advisor_sg_001"},
        ).json()
        action_id = actions["items"][0]["action_item_id"]
        body = {"action_item_version": 1, "acknowledged_by": "advisor_sg_001"}
        first = client.post(
            f"/advisory/cockpit/actions/{action_id}/acknowledgements",
            params={"portfolio_id": "PB_SG_GLOBAL_BAL_001", "advisor_id": "advisor_sg_001"},
            json=body,
            headers={"Idempotency-Key": "ack-api-001", "X-Correlation-ID": "corr-ack-api"},
        )
        replay = client.post(
            f"/advisory/cockpit/actions/{action_id}/acknowledgements",
            params={"portfolio_id": "PB_SG_GLOBAL_BAL_001", "advisor_id": "advisor_sg_001"},
            json=body,
            headers={"Idempotency-Key": "ack-api-001", "X-Correlation-ID": "corr-ack-api"},
        )
        stale = client.post(
            f"/advisory/cockpit/actions/{action_id}/acknowledgements",
            params={"portfolio_id": "PB_SG_GLOBAL_BAL_001", "advisor_id": "advisor_sg_001"},
            json={"action_item_version": 99, "acknowledged_by": "advisor_sg_001"},
            headers={"Idempotency-Key": "ack-api-stale"},
        )

    assert first.status_code == 200
    assert first.json()["replayed"] is False
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["action_item"]["status"] == "PENDING_REVIEW"
    assert stale.status_code == 422


def test_advisor_cockpit_openapi_documents_runtime_boundary() -> None:
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    assert "/advisory/cockpit/actions" in schema["paths"]
    assert "/advisory/cockpit/snapshot" in schema["paths"]
    assert "/advisory/cockpit/supportability" in schema["paths"]
    action_operation = schema["paths"]["/advisory/cockpit/actions"]["get"]
    supportability_operation = schema["paths"]["/advisory/cockpit/supportability"]["get"]
    acknowledgement_operation = schema["paths"][
        "/advisory/cockpit/actions/{action_item_id}/acknowledgements"
    ]["post"]

    assert action_operation["summary"] == "List Advisor Cockpit Actions"
    assert "Gateway and Workbench must render" in action_operation["description"]
    assert action_operation["responses"]["422"]["description"] == (
        "Advisor cockpit request failed validation, including invalid cursors."
    )
    assert "Gateway publication" in supportability_operation["description"]
    assert "active data-product posture" in supportability_operation["description"]
    assert "Acknowledgement does not clear blocking" in acknowledgement_operation["description"]
    assert acknowledgement_operation["responses"]["409"]["description"] == (
        "Idempotency key was reused with a different acknowledgement request."
    )
    assert any(
        parameter["name"] == "Idempotency-Key"
        and parameter["in"] == "header"
        and parameter["required"] is True
        for parameter in acknowledgement_operation["parameters"]
    )
