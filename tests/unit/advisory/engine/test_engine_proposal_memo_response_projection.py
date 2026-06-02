from datetime import datetime, timezone

from src.core.proposals.memo_response_projection import (
    archive_refs_from_report_posture,
    commentary_from_ai_event,
    latest_event_posture,
    memo_has_replay_metadata,
    memo_report_status,
    project_sections,
    to_audit_event,
)
from src.core.proposals.persistence_models import ProposalMemoEventRecord, ProposalMemoRecord


def _memo_event(*, event_type: str, reason: dict) -> ProposalMemoEventRecord:
    return ProposalMemoEventRecord(
        event_id="memo_event_1",
        memo_id="memo_1",
        proposal_id="proposal_1",
        proposal_version_no=1,
        event_type=event_type,
        actor_id="advisor_1",
        occurred_at=datetime(2026, 1, 15, 9, 30, tzinfo=timezone.utc),
        reason_json=reason,
    )


def test_memo_response_projection_helpers_project_event_posture_and_content() -> None:
    event = _memo_event(
        event_type="MEMO_AI_REFERENCE_RECORDED",
        reason={
            "memo_hash": "memo_hash_1",
            "ai_status": "UNAVAILABLE",
            "sections": [{"section_id": "executive_summary"}],
            "lineage": {"source": "fallback"},
            "review_guidance": ["Advisor review required."],
            "client_ready_publication": "BLOCKED",
        },
    )

    assert to_audit_event(event).reason["memo_hash"] == "memo_hash_1"
    assert latest_event_posture([event], event_type="MEMO_AI_REFERENCE_RECORDED") == {
        "status": "RECORDED",
        "event_id": "memo_event_1",
        "actor_id": "advisor_1",
        "occurred_at": "2026-01-15T09:30:00+00:00",
        "memo_hash": "memo_hash_1",
        "ai_status": "UNAVAILABLE",
        "sections": [{"section_id": "executive_summary"}],
        "lineage": {"source": "fallback"},
        "review_guidance": ["Advisor review required."],
        "client_ready_publication": "BLOCKED",
    }
    assert latest_event_posture([], event_type="MEMO_AI_REFERENCE_RECORDED") == {
        "status": "NOT_RECORDED"
    }
    assert commentary_from_ai_event(event)["status"] == "UNAVAILABLE"
    assert memo_report_status("COMPLETED_WITH_WARNINGS") == "RECORDED"
    assert memo_report_status("FAILED") == "BLOCKED"
    assert memo_report_status("ACCEPTED") == "DEGRADED"


def test_memo_response_projection_helpers_project_archive_and_replay_metadata() -> None:
    assert project_sections(
        {
            "sections": [
                {"section_id": "advisor", "audience_visibility": ["ADVISOR"]},
                {"section_id": "client", "audience_visibility": ["CLIENT"]},
                "invalid",
            ]
        },
        audience="ADVISOR",
    ) == [{"section_id": "advisor", "audience_visibility": ["ADVISOR"]}]
    assert archive_refs_from_report_posture(
        {
            "archive": {
                "archive_request_id": "archive_1",
                "document_id": "doc_1",
                "completed_at": "2026-01-15T09:31:00+00:00",
                "access_audit_ref": "audit_1",
            }
        }
    ) == [
        {
            "archive_request_id": "archive_1",
            "document_id": "doc_1",
            "completed_at": "2026-01-15T09:31:00+00:00",
            "retention_posture": "OWNED_BY_LOTUS_ARCHIVE",
            "legal_hold_posture": "OWNED_BY_LOTUS_ARCHIVE",
            "access_audit_ref": "audit_1",
        }
    ]

    memo = ProposalMemoRecord(
        memo_id="memo_1",
        proposal_id="proposal_1",
        proposal_version_no=1,
        memo_version="advisory-proposal-memo-evidence-pack.v1",
        memo_status="READY_FOR_ADVISOR_REVIEW",
        lifecycle_status="DRAFT",
        created_by="advisor_1",
        created_at=datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc),
        source_input_hash="source_hash_1",
        memo_hash="memo_hash_1",
        memo_json={"sections": []},
        replay_metadata_json={
            "proposal_request_hash": "proposal_request_hash_1",
            "proposal_artifact_hash": "proposal_artifact_hash_1",
            "proposal_simulation_hash": "proposal_simulation_hash_1",
            "memo_source_input_hash": "memo_source_input_hash_1",
            "memo_request_hash": "memo_request_hash_1",
            "replay_policy": "EXACT_SOURCE_HASH_MATCH",
        },
    )
    assert memo_has_replay_metadata(memo) is True
    memo.replay_metadata_json.pop("memo_request_hash")
    assert memo_has_replay_metadata(memo) is False
