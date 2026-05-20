from datetime import datetime, timezone

from src.core.proposals.execution_status import (
    build_execution_status_response,
    latest_execution_requested_event,
    latest_execution_status_event,
)
from src.core.proposals.models import ProposalRecord, ProposalWorkflowEventRecord


def _proposal() -> ProposalRecord:
    return ProposalRecord(
        proposal_id="pp_execution_projection",
        portfolio_id="pf_execution_projection",
        mandate_id="mandate_execution_projection",
        jurisdiction="SG",
        created_by="advisor_execution_projection",
        created_at=datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc),
        last_event_at=datetime(2026, 5, 20, 9, 20, tzinfo=timezone.utc),
        current_state="EXECUTED",
        current_version_no=2,
        title="Execution projection proposal",
    )


def _event(
    *,
    event_id: str,
    event_type: str,
    to_state: str,
    minute: int,
    reason_json: dict,
    related_version_no: int | None = 2,
) -> ProposalWorkflowEventRecord:
    return ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id="pp_execution_projection",
        event_type=event_type,
        from_state="EXECUTION_READY",
        to_state=to_state,
        actor_id="advisor_execution_projection",
        occurred_at=datetime(2026, 5, 20, 9, minute, tzinfo=timezone.utc),
        reason_json=reason_json,
        related_version_no=related_version_no,
    )


def test_execution_status_defaults_when_no_handoff_events_exist():
    response = build_execution_status_response(proposal=_proposal(), events=[])

    assert response.handoff_status == "NOT_REQUESTED"
    assert response.execution_request_id is None
    assert response.latest_workflow_event is None
    assert response.explanation == {
        "source": "ADVISORY_WORKFLOW_EVENTS",
        "state_correlation": "NO_EXECUTION_EVENTS_RECORDED",
    }


def test_execution_status_projects_latest_handoff_and_execution_event():
    requested = _event(
        event_id="pwe_request",
        event_type="EXECUTION_REQUESTED",
        to_state="EXECUTION_READY",
        minute=10,
        reason_json={
            "execution_request_id": "pex_projection",
            "execution_provider": "lotus-manage",
        },
    )
    partial = _event(
        event_id="pwe_partial",
        event_type="EXECUTION_PARTIALLY_EXECUTED",
        to_state="EXECUTION_READY",
        minute=15,
        reason_json={
            "execution_request_id": "pex_projection",
            "execution_provider": "lotus-manage",
            "external_execution_id": "oms_partial_projection",
        },
    )
    executed = _event(
        event_id="pwe_executed",
        event_type="EXECUTED",
        to_state="EXECUTED",
        minute=20,
        reason_json={
            "execution_request_id": "pex_projection",
            "execution_provider": "lotus-manage",
            "execution_id": "oms_fill_projection",
        },
    )

    response = build_execution_status_response(
        proposal=_proposal(),
        events=[requested, partial, executed],
    )

    assert latest_execution_requested_event([requested, partial, executed]) == requested
    assert latest_execution_status_event([requested, partial, executed]) == executed
    assert response.handoff_status == "EXECUTED"
    assert response.execution_request_id == "pex_projection"
    assert response.execution_provider == "lotus-manage"
    assert response.related_version_no == 2
    assert response.handoff_requested_at == "2026-05-20T09:10:00+00:00"
    assert response.executed_at == "2026-05-20T09:20:00+00:00"
    assert response.external_execution_id == "oms_fill_projection"
    assert response.latest_workflow_event is not None
    assert response.latest_workflow_event.event_id == "pwe_executed"
    assert response.explanation["state_correlation"] == "EXECUTION_REQUESTED_AND_EXECUTED_EVENTS"


def test_execution_status_can_be_derived_from_downstream_event_without_request_event():
    executed = _event(
        event_id="pwe_executed_only",
        event_type="EXECUTED",
        to_state="EXECUTED",
        minute=20,
        reason_json={
            "execution_request_id": "pex_projection",
            "execution_provider": "lotus-manage",
            "external_execution_id": "oms_fill_projection",
        },
        related_version_no=3,
    )

    response = build_execution_status_response(proposal=_proposal(), events=[executed])

    assert response.handoff_status == "EXECUTED"
    assert response.execution_request_id == "pex_projection"
    assert response.execution_provider == "lotus-manage"
    assert response.related_version_no == 3
    assert response.handoff_requested_at is None
    assert response.executed_at == "2026-05-20T09:20:00+00:00"
