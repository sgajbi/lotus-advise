from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

import src.api.proposals.router as proposals_router
import src.api.proposals.routes_advisory_copilot as copilot_routes
from src.api.main import app
from src.api.proposals.router import reset_proposal_workflow_service_for_tests
from src.core.policy_packs.models import PolicyEvaluationRecord
from src.core.proposals.models import ProposalMemoRecord, ProposalRecord, ProposalVersionRecord
from src.infrastructure.advisory_copilot import InMemoryAdvisoryCopilotRepository
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository
from src.integrations.lotus_ai import AdvisoryCopilotAiDraft

NOW = datetime(2026, 5, 28, 9, 0, tzinfo=UTC)


@pytest.fixture()
def copilot_repository(monkeypatch: pytest.MonkeyPatch) -> InMemoryAdvisoryCopilotRepository:
    reset_proposal_workflow_service_for_tests()
    repository = InMemoryAdvisoryCopilotRepository()
    app.dependency_overrides[copilot_routes.get_advisory_copilot_repository] = lambda: repository
    monkeypatch.setattr(proposals_router.runtime, "build_repository", InMemoryProposalRepository)
    yield repository
    app.dependency_overrides.pop(copilot_routes.get_advisory_copilot_repository, None)
    reset_proposal_workflow_service_for_tests()
    copilot_routes.reset_advisory_copilot_repository_for_tests()


def _evidence_packet_payload() -> dict[str, Any]:
    return {
        "evidence_packet_id": "copilot_packet_pb_sg_001",
        "action_family": "PROPOSAL_EXPLANATION",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "proposal_id": "proposal_sg_structured_note_001",
        "audience": "ADVISOR",
        "created_by": "advisor_123",
        "reason": {"business_reason": "Prepare advisor review."},
        "source_sections": [
            {
                "section_key": "POLICY_POSTURE",
                "title": "Policy posture",
                "evidence_class": "COMPLIANCE_REVIEW_EVIDENCE",
                "source_refs": [
                    {
                        "source_system": "lotus-advise",
                        "source_type": "POLICY_EVALUATION",
                        "source_id": "policy_eval_sg_001",
                        "content_hash": "sha256:policy-evaluation",
                        "access_class": "COMPLIANCE_REVIEW_EVIDENCE",
                    }
                ],
                "summary_items": ["Policy evaluation requires compliance review."],
                "allowed_audiences": ["ADVISOR", "COMPLIANCE_REVIEWER"],
            }
        ],
    }


def _seed_proposal_version(repository: InMemoryProposalRepository) -> None:
    repository.create_proposal(
        ProposalRecord(
            proposal_id="proposal_sg_structured_note_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            created_by="advisor_123",
            created_at=NOW,
            last_event_at=NOW,
            current_state="COMPLIANCE_REVIEW",
            current_version_no=1,
            title="Structured note proposal review",
        )
    )
    repository.create_version(
        ProposalVersionRecord(
            proposal_version_id="version_sg_001",
            proposal_id="proposal_sg_structured_note_001",
            version_no=1,
            created_at=NOW,
            request_hash="sha256:request",
            artifact_hash="sha256:artifact",
            simulation_hash="sha256:simulation",
            status_at_creation="READY",
            proposal_result_json={"status": "READY"},
            artifact_json={"narrative": {"status": "REVIEW_REQUIRED"}},
            evidence_bundle_json={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
        )
    )
    repository.create_memo(
        ProposalMemoRecord(
            memo_id="memo_sg_001",
            proposal_id="proposal_sg_structured_note_001",
            proposal_version_no=1,
            proposal_version_id="version_sg_001",
            artifact_id="artifact_sg_001",
            memo_version="advisory-proposal-memo-evidence-pack.v1",
            memo_status="BLOCKED",
            lifecycle_status="FINALIZED",
            created_by="advisor_123",
            created_at=NOW,
            source_input_hash="sha256:memo-source",
            memo_hash="sha256:memo",
            memo_json={"memo_id": "memo_sg_001"},
            report_package_events_json=[
                {"event_id": "memo_report_pkg_001", "report_reference_id": "report_pkg_001"}
            ],
        )
    )


def _policy_evaluation() -> PolicyEvaluationRecord:
    return PolicyEvaluationRecord(
        evaluation_id="policy_eval_sg_001",
        proposal_id="proposal_sg_structured_note_001",
        proposal_version_id="version_sg_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        generated_at="2026-05-28T09:00:00+00:00",
        created_by="advisor_123",
        evaluation_status="PENDING_REVIEW",
        policy_content_hash="sha256:policy-content",
        source_evidence_hash="sha256:source-evidence",
        evaluation_hash="sha256:policy-evaluation",
        evaluation_json={"evaluation_status": "PENDING_REVIEW"},
        approval_dependencies=["COMPLIANCE_REVIEW"],
    )


def test_advisory_copilot_evidence_packet_create_and_read(
    copilot_repository: InMemoryAdvisoryCopilotRepository,
) -> None:
    _ = copilot_repository
    with TestClient(app) as client:
        created = client.post(
            "/advisory/copilot/evidence-packets",
            json=_evidence_packet_payload(),
            headers={"X-Correlation-ID": "corr_packet_001"},
        )
        read = client.get("/advisory/copilot/evidence-packets/copilot_packet_pb_sg_001")

    assert created.status_code == 201
    assert read.status_code == 200
    payload = read.json()
    assert payload["evidence_packet"]["client_ready_publication"] == "BLOCKED"
    assert payload["record"]["correlation_id"] == "corr_packet_001"
    assert {item["reason_code"] for item in payload["evidence_packet"]["unsupported_evidence"]} == {
        "SOURCE_NOT_AVAILABLE"
    }


def test_advisory_copilot_evidence_packet_from_proposal_version_is_source_owned(
    monkeypatch: pytest.MonkeyPatch,
    copilot_repository: InMemoryAdvisoryCopilotRepository,
) -> None:
    _ = copilot_repository
    proposal_repository = InMemoryProposalRepository()
    _seed_proposal_version(proposal_repository)
    monkeypatch.setattr(proposals_router.runtime, "build_repository", lambda: proposal_repository)
    reset_proposal_workflow_service_for_tests()
    monkeypatch.setattr(
        copilot_routes,
        "list_policy_evaluation_records",
        lambda **_: [_policy_evaluation()],
    )

    with TestClient(app) as client:
        response = client.post(
            "/advisory/copilot/evidence-packets/from-proposal-version",
            json={
                "proposal_id": "proposal_sg_structured_note_001",
                "proposal_version_no": 1,
                "action_family": "PROPOSAL_EXPLANATION",
                "audience": "ADVISOR",
                "created_by": "advisor_123",
                "reason": {"business_reason": "Prepare advisor copilot review."},
            },
            headers={"X-Correlation-ID": "corr_projection_001"},
        )

    assert response.status_code == 201
    payload = response.json()
    packet = payload["evidence_packet"]
    assert packet["portfolio_id"] == "PB_SG_GLOBAL_BAL_001"
    assert packet["client_ready_publication"] == "BLOCKED"
    assert {section["section_key"] for section in packet["sections"]} >= {
        "PROPOSAL_CONTEXT",
        "NARRATIVE_POSTURE",
        "MEMO_EVIDENCE",
        "POLICY_POSTURE",
    }
    assert "REPORT_READINESS" not in {
        item["reason_code"] for item in packet["unsupported_evidence"]
    }
    assert "raw prompt" not in str(payload).lower()
    assert payload["record"]["reason_json"]["source_projection"] == "PROPOSAL_VERSION"


def test_proposal_version_copilot_packet_preserves_version_lineage_for_every_action(
    monkeypatch: pytest.MonkeyPatch,
    copilot_repository: InMemoryAdvisoryCopilotRepository,
) -> None:
    _ = copilot_repository
    proposal_repository = InMemoryProposalRepository()
    _seed_proposal_version(proposal_repository)
    monkeypatch.setattr(proposals_router.runtime, "build_repository", lambda: proposal_repository)
    reset_proposal_workflow_service_for_tests()
    monkeypatch.setattr(
        copilot_routes,
        "list_policy_evaluation_records",
        lambda **_: [_policy_evaluation()],
    )

    with TestClient(app) as client:
        response = client.post(
            "/advisory/copilot/evidence-packets/from-proposal-version",
            json={
                "proposal_id": "proposal_sg_structured_note_001",
                "proposal_version_no": 1,
                "action_family": "MEETING_PREPARATION",
                "audience": "ADVISOR",
                "created_by": "advisor_123",
                "reason": {"business_reason": "Prepare advisor meeting."},
            },
        )

    assert response.status_code == 201
    packet = response.json()["evidence_packet"]
    assert "PROPOSAL_CONTEXT" not in {section["section_key"] for section in packet["sections"]}
    assert {
        (lineage["lineage_type"], lineage["lineage_id"]) for lineage in packet["lineage_refs"]
    } >= {
        ("PROPOSAL_VERSION", "version_sg_001"),
        ("PROPOSAL_VERSION_NO", "1"),
    }


def test_proposal_version_copilot_packet_refreshes_same_projection_when_hash_changes(
    monkeypatch: pytest.MonkeyPatch,
    copilot_repository: InMemoryAdvisoryCopilotRepository,
) -> None:
    _ = copilot_repository
    proposal_repository = InMemoryProposalRepository()
    _seed_proposal_version(proposal_repository)
    monkeypatch.setattr(proposals_router.runtime, "build_repository", lambda: proposal_repository)
    reset_proposal_workflow_service_for_tests()
    policy_record = _policy_evaluation()
    monkeypatch.setattr(
        copilot_routes,
        "list_policy_evaluation_records",
        lambda **_: [policy_record],
    )
    request = {
        "proposal_id": "proposal_sg_structured_note_001",
        "proposal_version_no": 1,
        "action_family": "PROPOSAL_EXPLANATION",
        "audience": "ADVISOR",
        "created_by": "advisor_123",
        "reason": {"business_reason": "Prepare advisor copilot review."},
    }

    with TestClient(app) as client:
        first = client.post(
            "/advisory/copilot/evidence-packets/from-proposal-version",
            json=request,
        )
        policy_record = policy_record.model_copy(
            update={
                "evaluation_hash": "sha256:refreshed-policy-evaluation",
                "approval_dependencies": ["COMPLIANCE_REVIEW", "UPDATED_SOURCE_EVIDENCE"],
            }
        )
        second = client.post(
            "/advisory/copilot/evidence-packets/from-proposal-version",
            json=request,
        )

    assert first.status_code == 201
    assert second.status_code == 201
    assert (
        first.json()["evidence_packet"]["evidence_packet_id"]
        == (second.json()["evidence_packet"]["evidence_packet_id"])
    )
    assert (
        first.json()["evidence_packet"]["evidence_packet_hash"]
        != (second.json()["evidence_packet"]["evidence_packet_hash"])
    )


def test_advisory_copilot_action_persists_review_gated_run(
    monkeypatch: pytest.MonkeyPatch,
    copilot_repository: InMemoryAdvisoryCopilotRepository,
) -> None:
    _ = copilot_repository

    def _draft(**_: Any) -> AdvisoryCopilotAiDraft:
        return AdvisoryCopilotAiDraft(
            status="REVIEW_REQUIRED",
            sections=(
                {
                    "section_key": "SUMMARY",
                    "title": "Advisor summary",
                    "text": "Policy review is required before client communication.",
                },
            ),
            lineage={
                "workflow_pack_id": "advisory_copilot_proposal_explanation.pack",
                "workflow_pack_version": "v1",
                "workflow_run_id": "packrun_copilot_001",
                "model_version": "stub-advisory-copilot-v1",
                "prompt_template_version": "advisory-copilot-prompt-template.v1",
                "output_schema_version": "advisory-copilot-output-schema.v1",
                "evaluation_pack_ref": "advisory-copilot-eval-pack.v1",
                "proposal_version_id": "version_sg_001",
            },
            review_guidance=("Review source evidence before internal use.",),
            guardrail_reasons=(),
        )

    monkeypatch.setattr(copilot_routes, "generate_advisory_copilot_draft_with_lotus_ai", _draft)

    with TestClient(app) as client:
        client.post("/advisory/copilot/evidence-packets", json=_evidence_packet_payload())
        created = client.post(
            "/advisory/copilot/actions",
            json={
                "evidence_packet_id": "copilot_packet_pb_sg_001",
                "audience": "ADVISOR",
                "requested_outputs": ["advisor_review_summary"],
                "requested_by": "advisor_123",
                "reason": {"business_reason": "Prepare advisor review."},
                "requested_intents": ["explain_policy_posture"],
                "user_instruction": "Summarize the advisory evidence for internal review.",
            },
            headers={
                "Idempotency-Key": "copilot-action-idem-001",
                "X-Correlation-ID": "corr_action_001",
            },
        )
        replay = client.post(
            "/advisory/copilot/actions",
            json={
                "evidence_packet_id": "copilot_packet_pb_sg_001",
                "audience": "ADVISOR",
                "requested_outputs": ["advisor_review_summary"],
                "requested_by": "advisor_123",
                "reason": {"business_reason": "Prepare advisor review."},
                "requested_intents": ["explain_policy_posture"],
                "user_instruction": "Summarize the advisory evidence for internal review.",
            },
            headers={"Idempotency-Key": "copilot-action-idem-001"},
        )
        run_id = created.json()["run"]["run_id"]
        read = client.get(f"/advisory/copilot/actions/{run_id}")
        version_runs = client.get(
            "/advisory/proposals/proposal_sg_structured_note_001/versions/"
            "version_sg_001/copilot-runs"
        )

    assert created.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert read.json()["run"]["review_posture"] == "REVIEW_REQUIRED"
    assert read.json()["reviews"] == []
    assert version_runs.json()["items"][0]["run_id"] == run_id
    assert "Summarize the advisory evidence" not in str(read.json())


def test_proposal_version_copilot_runs_are_paginated(
    monkeypatch: pytest.MonkeyPatch,
    copilot_repository: InMemoryAdvisoryCopilotRepository,
) -> None:
    _ = copilot_repository
    monkeypatch.setattr(
        copilot_routes,
        "generate_advisory_copilot_draft_with_lotus_ai",
        lambda **_: AdvisoryCopilotAiDraft(
            status="REVIEW_REQUIRED",
            sections=(
                {
                    "section_key": "SUMMARY",
                    "title": "Advisor summary",
                    "text": "Policy review is required before client communication.",
                },
            ),
            lineage={
                "workflow_pack_id": "advisory_copilot_proposal_explanation.pack",
                "proposal_version_id": "version_sg_001",
            },
            review_guidance=("Review source evidence before internal use.",),
            guardrail_reasons=(),
        ),
    )

    with TestClient(app) as client:
        client.post("/advisory/copilot/evidence-packets", json=_evidence_packet_payload())
        run_ids: set[str] = set()
        for index in range(3):
            response = client.post(
                "/advisory/copilot/actions",
                json={
                    "evidence_packet_id": "copilot_packet_pb_sg_001",
                    "audience": "ADVISOR",
                    "requested_outputs": ["advisor_review_summary"],
                    "requested_by": "advisor_123",
                    "reason": {"business_reason": "Prepare advisor review."},
                    "user_instruction": f"Prepare internal review pass {index}.",
                },
                headers={"Idempotency-Key": f"copilot-action-idem-page-{index}"},
            )
            assert response.status_code == 200
            run_ids.add(response.json()["run"]["run_id"])

        first_page = client.get(
            "/advisory/proposals/proposal_sg_structured_note_001/versions/"
            "version_sg_001/copilot-runs",
            params={"limit": 2},
        )
        second_page = client.get(
            "/advisory/proposals/proposal_sg_structured_note_001/versions/"
            "version_sg_001/copilot-runs",
            params={"limit": 2, "cursor": first_page.json()["next_cursor"]},
        )
        invalid_cursor = client.get(
            "/advisory/proposals/proposal_sg_structured_note_001/versions/"
            "version_sg_001/copilot-runs",
            params={"cursor": "not-a-valid-cursor"},
        )

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert invalid_cursor.status_code == 422
    assert len(first_page.json()["items"]) == 2
    assert first_page.json()["next_cursor"] is not None
    assert len(second_page.json()["items"]) == 1
    assert second_page.json()["next_cursor"] is None
    paged_ids = {
        item["run_id"] for item in first_page.json()["items"] + second_page.json()["items"]
    }
    assert paged_ids == run_ids


def test_advisory_copilot_review_api_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    copilot_repository: InMemoryAdvisoryCopilotRepository,
) -> None:
    _ = copilot_repository
    monkeypatch.setattr(
        copilot_routes,
        "generate_advisory_copilot_draft_with_lotus_ai",
        lambda **_: AdvisoryCopilotAiDraft(
            status="REVIEW_REQUIRED",
            sections=(),
            lineage={"workflow_pack_id": "advisory_copilot_proposal_explanation.pack"},
            review_guidance=(),
            guardrail_reasons=(),
        ),
    )

    with TestClient(app) as client:
        client.post("/advisory/copilot/evidence-packets", json=_evidence_packet_payload())
        run = client.post(
            "/advisory/copilot/actions",
            json={
                "evidence_packet_id": "copilot_packet_pb_sg_001",
                "audience": "ADVISOR",
                "requested_outputs": ["advisor_review_summary"],
                "requested_by": "advisor_123",
                "reason": {"business_reason": "Prepare advisor review."},
            },
        ).json()["run"]
        first = client.post(
            f"/advisory/copilot/actions/{run['run_id']}/reviews",
            json={
                "action": "APPROVE_FOR_INTERNAL_USE",
                "actor_id": "supervisor_123",
                "reason": {"decision": "Reviewed against cited source evidence."},
            },
            headers={"Idempotency-Key": "copilot-review-idem-001"},
        )
        replay = client.post(
            f"/advisory/copilot/actions/{run['run_id']}/reviews",
            json={
                "action": "APPROVE_FOR_INTERNAL_USE",
                "actor_id": "supervisor_123",
                "reason": {"decision": "Reviewed against cited source evidence."},
            },
            headers={"Idempotency-Key": "copilot-review-idem-001"},
        )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert first.json()["run"]["review_posture"] == "APPROVED_FOR_INTERNAL_USE"


def test_advisory_copilot_openapi_is_action_specific() -> None:
    app.openapi_schema = None
    schema = app.openapi()

    paths = schema["paths"]
    assert "/advisory/copilot/actions" in paths
    assert "/advisory/copilot/actions/{run_id}" in paths
    assert "/advisory/copilot/actions/{run_id}/reviews" in paths
    assert "/advisory/copilot/evidence-packets" in paths
    assert "/advisory/copilot/evidence-packets/from-proposal-version" in paths
    assert "/advisory/copilot/supportability" in paths
    assert "/advisory/copilot/prompt" not in paths
    assert "Advisory Copilot" in {tag["name"] for tag in schema["tags"]}
