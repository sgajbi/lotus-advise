from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import src.api.proposals.router as proposals_router
import src.core.advisor_cockpit.service as cockpit_service
from src.api.main import app
from src.api.proposals.cockpit_dependencies import get_advisor_cockpit_service
from src.api.proposals.cockpit_responses import (
    ADVISOR_COCKPIT_ACKNOWLEDGEMENT_RESPONSES,
    ADVISOR_COCKPIT_READ_RESPONSES,
)
from src.api.proposals.router import reset_proposal_workflow_service_for_tests
from src.core.advisor_cockpit import (
    AdvisorCockpitPreparationPacketPage,
    AdvisorCockpitSupportabilityResponse,
    MeetingPreparationPacket,
)
from src.core.policy_packs.persistence_models import PolicyEvaluationRecord
from src.core.proposals.models import ProposalMemoRecord, ProposalRecord
from src.core.tactical_house_view import clear_tactical_house_view_affected_cohorts_for_tests
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository

NOW = datetime(2026, 5, 27, 8, 0, tzinfo=UTC)


def setup_function() -> None:
    reset_proposal_workflow_service_for_tests()
    clear_tactical_house_view_affected_cohorts_for_tests()


def _preparation_packet(packet_id: str = "prep_proposal_sg_001_v1") -> MeetingPreparationPacket:
    return MeetingPreparationPacket(
        packet_id=packet_id,
        context_type="PROPOSAL",
        context_ref="proposal_sg_001",
        status="READY",
        sections=[
            {
                "section_id": "advisor_meeting_context",
                "title": "Advisor meeting context",
                "summary": "Active advisory proposal is available for meeting preparation.",
            }
        ],
    )


def test_advisor_cockpit_api_models_reject_unbounded_preparation_pages() -> None:
    packet = _preparation_packet()

    with pytest.raises(ValidationError, match="List should have at most 64 items"):
        AdvisorCockpitPreparationPacketPage(
            items=[packet for _ in range(65)],
            page_size=25,
            total_count=65,
        )

    with pytest.raises(ValidationError, match="greater than or equal to 1"):
        AdvisorCockpitPreparationPacketPage(
            items=[packet],
            page_size=0,
            total_count=1,
        )

    with pytest.raises(ValidationError, match="less than or equal to 100"):
        AdvisorCockpitPreparationPacketPage(
            items=[packet],
            page_size=101,
            total_count=1,
        )

    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        AdvisorCockpitPreparationPacketPage(
            items=[packet],
            page_size=25,
            total_count=-1,
        )


def test_advisor_cockpit_api_models_reject_unbounded_supportability_context() -> None:
    with pytest.raises(ValidationError, match="String should have at most 160 characters"):
        AdvisorCockpitSupportabilityResponse(
            posture="X" * 161,
            supportability={},
            unsupported_capabilities=[],
        )

    with pytest.raises(ValidationError, match="Dictionary should have at most 64 items"):
        AdvisorCockpitSupportabilityResponse(
            posture="ADVISE_GATEWAY_WORKBENCH_CANONICAL_PROOF_SUPPORTED",
            supportability={f"key_{index}": "SUPPORTED" for index in range(65)},
            unsupported_capabilities=[],
        )

    with pytest.raises(ValidationError, match="List should have at most 64 items"):
        AdvisorCockpitSupportabilityResponse(
            posture="ADVISE_GATEWAY_WORKBENCH_CANONICAL_PROOF_SUPPORTED",
            supportability={},
            unsupported_capabilities=[f"UNSUPPORTED_{index}" for index in range(65)],
        )


def test_advisor_cockpit_dependency_wires_shared_proposal_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryProposalRepository()
    monkeypatch.setattr(proposals_router, "get_proposal_repository", lambda: repository)

    service = get_advisor_cockpit_service()

    assert getattr(service, "_repository") is repository


def test_advisor_cockpit_response_metadata_stays_route_family_specific() -> None:
    assert ADVISOR_COCKPIT_READ_RESPONSES[422]["description"] == (
        "Advisor cockpit request failed validation, including invalid cursors."
    )
    assert ADVISOR_COCKPIT_ACKNOWLEDGEMENT_RESPONSES[409]["description"] == (
        "Idempotency key was reused with a different acknowledgement request."
    )


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
    assert action_payload["total_count"] == 4
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


def test_advisor_cockpit_api_projects_compliance_queue_by_caller_role(
    cockpit_repository: InMemoryProposalRepository,
) -> None:
    _ = cockpit_repository
    with TestClient(app) as client:
        response = client.get(
            "/advisory/cockpit/actions",
            params={
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "role": "COMPLIANCE_REVIEWER",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_count"] == 2
    assert {item["action_family"] for item in payload["items"]} == {
        "POLICY_REVIEW_REQUIRED",
        "APPROVAL_DEPENDENCY_AGING",
    }
    assert {item["owner_role"] for item in payload["items"]} == {"COMPLIANCE_REVIEWER"}


def test_advisor_cockpit_api_projects_source_backed_house_view_queue(
    cockpit_repository: InMemoryProposalRepository,
) -> None:
    _ = cockpit_repository
    with TestClient(app) as client:
        house_view = client.post(
            "/advisory/tactical-house-view/cohorts/evaluate",
            json=_house_view_payload(),
        )
        response = client.get(
            "/advisory/cockpit/actions",
            params={
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "role": "PORTFOLIO_MANAGER",
            },
            headers={"X-Correlation-ID": "corr-cockpit-house-view"},
        )

    assert house_view.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_count"] == 1
    action = payload["items"][0]
    assert action["action_family"] == "HOUSE_VIEW_IMPACT_REVIEW"
    assert action["owner_role"] == "PORTFOLIO_MANAGER"
    assert action["owner_role_label"] == "Portfolio manager"
    assert action["evidence_refs"][0]["evidence_type"] == "TACTICAL_HOUSE_VIEW_COHORT"
    assert action["correlation_id"] == "corr-cockpit-house-view"

    with TestClient(app) as client:
        legacy_response = client.get(
            "/advisory/cockpit/actions",
            params={
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "role": "DPM_OWNER",
            },
            headers={"X-Correlation-ID": "corr-cockpit-house-view-legacy"},
        )

    assert legacy_response.status_code == 200
    legacy_action = legacy_response.json()["items"][0]
    assert legacy_action["action_family"] == "HOUSE_VIEW_IMPACT_REVIEW"
    assert legacy_action["owner_role"] == "PORTFOLIO_MANAGER"
    assert legacy_action["owner_role_label"] == "Portfolio manager"


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
        blank_actor = client.post(
            f"/advisory/cockpit/actions/{action_id}/acknowledgements",
            params={"portfolio_id": "PB_SG_GLOBAL_BAL_001", "advisor_id": "advisor_sg_001"},
            json={"action_item_version": 1, "acknowledged_by": "   "},
            headers={"Idempotency-Key": "ack-api-blank-actor"},
        )

    assert first.status_code == 200
    assert first.json()["replayed"] is False
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["action_item"]["status"] == "PENDING_REVIEW"
    assert stale.status_code == 422
    assert blank_actor.status_code == 422


def test_advisor_cockpit_api_rejects_oversized_route_inputs(
    cockpit_repository: InMemoryProposalRepository,
) -> None:
    _ = cockpit_repository
    oversized_ref = "x" * 161
    with TestClient(app) as client:
        actions = client.get(
            "/advisory/cockpit/actions",
            params={"portfolio_id": "PB_SG_GLOBAL_BAL_001", "advisor_id": "advisor_sg_001"},
        ).json()
        action_id = actions["items"][0]["action_item_id"]
        oversized_query = client.get(
            "/advisory/cockpit/actions",
            params={"portfolio_id": "PB_SG_GLOBAL_BAL_001", "advisor_id": oversized_ref},
        )
        oversized_cursor = client.get(
            "/advisory/cockpit/preparation-packets",
            params={"portfolio_id": "PB_SG_GLOBAL_BAL_001", "cursor": oversized_ref},
        )
        oversized_path = client.get(f"/advisory/cockpit/actions/{oversized_ref}")
        oversized_header = client.post(
            f"/advisory/cockpit/actions/{action_id}/acknowledgements",
            params={"portfolio_id": "PB_SG_GLOBAL_BAL_001", "advisor_id": "advisor_sg_001"},
            headers={"Idempotency-Key": oversized_ref},
            json={"action_item_version": 1, "acknowledged_by": "advisor_sg_001"},
        )

    assert oversized_query.status_code == 422
    assert oversized_cursor.status_code == 422
    assert oversized_path.status_code == 422
    assert oversized_header.status_code == 422


def test_advisor_cockpit_openapi_documents_runtime_boundary() -> None:
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    assert "/advisory/cockpit/actions" in schema["paths"]
    assert "/advisory/cockpit/actions/{action_item_id}" in schema["paths"]
    assert "/advisory/cockpit/actions/{action_item_id}/acknowledgements" in schema["paths"]
    assert "/advisory/cockpit/preparation-packets" in schema["paths"]
    assert "/advisory/cockpit/snapshot" in schema["paths"]
    assert "/advisory/cockpit/supportability" in schema["paths"]
    assert "/advisory/cockpit/action-items" not in schema["paths"]
    assert "/advisory/cockpit/supervision/approval-queue" not in schema["paths"]
    action_operation = schema["paths"]["/advisory/cockpit/actions"]["get"]
    preparation_operation = schema["paths"]["/advisory/cockpit/preparation-packets"]["get"]
    supportability_operation = schema["paths"]["/advisory/cockpit/supportability"]["get"]
    acknowledgement_operation = schema["paths"][
        "/advisory/cockpit/actions/{action_item_id}/acknowledgements"
    ]["post"]

    assert action_operation["summary"] == "List Advisor Cockpit Actions"
    assert "Gateway and Workbench must render" in action_operation["description"]
    assert action_operation["responses"]["422"]["description"] == (
        "Advisor cockpit request failed validation, including invalid cursors."
    )
    action_schema = schema["components"]["schemas"]["AdvisoryActionItem"]
    emitted_owner_values = action_schema["properties"]["owner_role"]["enum"]
    assert "PORTFOLIO_MANAGER" in emitted_owner_values
    assert "DPM_OWNER" not in emitted_owner_values
    role_parameter = next(
        parameter for parameter in action_operation["parameters"] if parameter["name"] == "role"
    )
    assert "legacy caller alias" in role_parameter["description"]
    assert "DPM_OWNER" in role_parameter["schema"]["enum"]
    assert "PORTFOLIO_MANAGER" in role_parameter["schema"]["enum"]
    assert preparation_operation["summary"] == "List Advisor Cockpit Preparation Packets"
    assert "Gateway and Workbench must render these packets" in preparation_operation["description"]
    assert "calendar" in preparation_operation["description"]
    assert any(
        parameter["name"] == "cursor"
        and parameter["in"] == "query"
        and "preparation-packet cursor" in parameter["description"]
        and _max_length(parameter["schema"]) == 160
        for parameter in preparation_operation["parameters"]
    )
    assert any(
        parameter["name"] == "advisor_id"
        and parameter["in"] == "query"
        and _max_length(parameter["schema"]) == 160
        for parameter in action_operation["parameters"]
    )
    assert any(
        parameter["name"] == "limit"
        and parameter["in"] == "query"
        and parameter["schema"]["maximum"] == 100
        for parameter in action_operation["parameters"]
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
        and _max_length(parameter["schema"]) == 128
        for parameter in acknowledgement_operation["parameters"]
    )


def _max_length(parameter_schema: dict) -> int | None:
    if "maxLength" in parameter_schema:
        return parameter_schema["maxLength"]
    for option in parameter_schema.get("anyOf", []):
        if isinstance(option, dict) and "maxLength" in option:
            return option["maxLength"]
    return None


def _house_view_payload() -> dict:
    return {
        "tactical_view": {
            "tactical_view_id": "thv_2026_05_asia_duration",
            "tactical_view_version": "2026.05",
            "theme_id": "asia_duration_reduce",
            "as_of_date": "2026-05-14",
            "target_action": "REDUCE",
            "rationale": "Reduce duration exposure in Asia balanced discretionary books.",
            "source_refs": [
                {
                    "source_system": "lotus-advise",
                    "source_type": "TACTICAL_HOUSE_VIEW",
                    "source_id": "thv_2026_05_asia_duration",
                    "source_version": "2026.05",
                    "content_hash": "sha256:house-view",
                }
            ],
        },
        "candidate_portfolios": [
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
                "portfolio_type": "DISCRETIONARY",
                "discretionary_mandate": True,
                "booking_center_code": "Singapore",
                "current_exposure_weight": "0.18",
                "alignment_signal": "OVERWEIGHT",
                "source_refs": [
                    {
                        "source_system": "lotus-core",
                        "source_type": "HoldingsAsOf",
                        "source_id": "holdings:PB_SG_GLOBAL_BAL_001:2026-05-14",
                        "source_version": "v1",
                        "content_hash": "sha256:holdings",
                    }
                ],
            }
        ],
        "eligible_portfolio_types": ["DISCRETIONARY"],
        "correlation_id": "corr-thv-001",
    }
