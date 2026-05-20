from datetime import datetime, timezone

from src.core.proposals.execution_handoff import (
    build_execution_handoff_replay_response,
    build_execution_handoff_requested_event,
    build_execution_handoff_response,
)
from src.core.proposals.models import (
    ProposalExecutionHandoffRequest,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)


def _proposal() -> ProposalRecord:
    return ProposalRecord(
        proposal_id="pp_execution_handoff",
        portfolio_id="pf_execution_handoff",
        mandate_id="mandate_execution_handoff",
        jurisdiction="SG",
        created_by="advisor_execution",
        created_at=datetime(2026, 5, 21, 9, 0, tzinfo=timezone.utc),
        last_event_at=datetime(2026, 5, 21, 9, 5, tzinfo=timezone.utc),
        current_state="EXECUTION_READY",
        current_version_no=3,
        title="Execution handoff test",
        lifecycle_origin="DIRECT_CREATE",
        source_workspace_id=None,
    )


def _payload(**overrides) -> ProposalExecutionHandoffRequest:
    values = {
        "actor_id": "ops_execution",
        "execution_provider": "lotus-manage",
        "related_version_no": None,
        "expected_state": "EXECUTION_READY",
        "correlation_id": "corr_execution",
        "external_request_id": None,
        "notes": {"priority": "STANDARD"},
    }
    values.update(overrides)
    return ProposalExecutionHandoffRequest(**values)


def test_build_execution_handoff_requested_event_preserves_audit_payload():
    event = build_execution_handoff_requested_event(
        event_id="pwe_execution_handoff",
        proposal=_proposal(),
        payload=_payload(external_request_id="oms_req_001", related_version_no=2),
        occurred_at=datetime(2026, 5, 21, 9, 10, tzinfo=timezone.utc),
        execution_request_id="oms_req_001",
        idempotency_key="idem_execution_handoff",
        request_hash="sha256:handoff",
    )

    assert event.event_type == "EXECUTION_REQUESTED"
    assert event.from_state == "EXECUTION_READY"
    assert event.to_state == "EXECUTION_READY"
    assert event.actor_id == "ops_execution"
    assert event.related_version_no == 2
    assert event.reason_json == {
        "execution_request_id": "oms_req_001",
        "execution_provider": "lotus-manage",
        "correlation_id": "corr_execution",
        "external_request_id": "oms_req_001",
        "notes": {"priority": "STANDARD"},
        "idempotency_key": "idem_execution_handoff",
        "idempotency_request_hash": "sha256:handoff",
    }


def test_build_execution_handoff_requested_event_defaults_to_current_version():
    event = build_execution_handoff_requested_event(
        event_id="pwe_execution_handoff",
        proposal=_proposal(),
        payload=_payload(correlation_id=None, notes={}),
        occurred_at=datetime(2026, 5, 21, 9, 10, tzinfo=timezone.utc),
        execution_request_id="pex_execution",
        idempotency_key=None,
        request_hash="sha256:handoff",
    )

    assert event.related_version_no == 3
    assert event.reason_json == {
        "execution_request_id": "pex_execution",
        "execution_provider": "lotus-manage",
        "notes": {},
    }


def test_execution_handoff_response_projects_recorded_event():
    proposal = _proposal()
    event = ProposalWorkflowEventRecord(
        event_id="pwe_execution_handoff",
        proposal_id=proposal.proposal_id,
        event_type="EXECUTION_REQUESTED",
        from_state="EXECUTION_READY",
        to_state="EXECUTION_READY",
        actor_id="ops_execution",
        occurred_at=datetime(2026, 5, 21, 9, 10, tzinfo=timezone.utc),
        reason_json={
            "execution_request_id": "pex_execution",
            "execution_provider": "lotus-manage",
        },
        related_version_no=3,
    )

    response = build_execution_handoff_response(
        proposal=proposal,
        event=event,
        execution_request_id="pex_execution",
        execution_provider="lotus-manage",
    )

    assert response.execution_request_id == "pex_execution"
    assert response.handoff_status == "REQUESTED"
    assert response.latest_workflow_event.event_type == "EXECUTION_REQUESTED"


def test_execution_handoff_replay_response_uses_replayed_event_identity():
    proposal = _proposal()
    replay_event = ProposalWorkflowEventRecord(
        event_id="pwe_replayed_handoff",
        proposal_id=proposal.proposal_id,
        event_type="EXECUTION_REQUESTED",
        from_state="EXECUTION_READY",
        to_state="EXECUTION_READY",
        actor_id="ops_execution",
        occurred_at=datetime(2026, 5, 21, 9, 10, tzinfo=timezone.utc),
        reason_json={
            "execution_request_id": "oms_replay",
            "execution_provider": "lotus-manage",
        },
        related_version_no=3,
    )

    response = build_execution_handoff_replay_response(
        proposal=proposal,
        replay_event=replay_event,
    )

    assert response.execution_request_id == "oms_replay"
    assert response.execution_provider == "lotus-manage"
    assert response.latest_workflow_event.event_id == "pwe_replayed_handoff"
