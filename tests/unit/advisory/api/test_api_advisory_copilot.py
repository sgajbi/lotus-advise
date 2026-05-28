from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import src.api.proposals.router as proposals_router
import src.api.proposals.routes_advisory_copilot as copilot_routes
from src.api.main import app
from src.api.proposals.router import reset_proposal_workflow_service_for_tests
from src.infrastructure.advisory_copilot import InMemoryAdvisoryCopilotRepository
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository
from src.integrations.lotus_ai import AdvisoryCopilotAiDraft


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
    assert "/advisory/copilot/supportability" in paths
    assert "/advisory/copilot/prompt" not in paths
    assert "Advisory Copilot" in {tag["name"] for tag in schema["tags"]}
