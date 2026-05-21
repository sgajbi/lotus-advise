from datetime import datetime, timezone

from src.core.proposals.delivery_summary import (
    build_delivery_history_response,
    build_delivery_summary_from_events,
    build_delivery_summary_response,
    select_delivery_events,
)
from src.core.proposals.execution_boundary import execution_ownership_boundary
from src.core.proposals.models import ProposalRecord, ProposalWorkflowEventRecord


def _proposal() -> ProposalRecord:
    return ProposalRecord(
        proposal_id="pp_delivery_summary",
        portfolio_id="pf_delivery_summary",
        mandate_id="mandate_delivery_summary",
        jurisdiction="SG",
        created_by="advisor_delivery",
        created_at=datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc),
        last_event_at=datetime(2026, 5, 20, 11, 0, tzinfo=timezone.utc),
        current_state="EXECUTION_READY",
        current_version_no=1,
        title="Delivery projection test",
        lifecycle_origin="DIRECT_CREATE",
        source_workspace_id=None,
    )


def _event(
    event_type: str,
    *,
    reason_json: dict | None = None,
    related_version_no: int | None = 1,
    occurred_at: datetime | None = None,
) -> ProposalWorkflowEventRecord:
    return ProposalWorkflowEventRecord(
        event_id=f"pwe_{event_type.lower()}",
        proposal_id="pp_delivery_summary",
        event_type=event_type,
        from_state="EXECUTION_READY",
        to_state="EXECUTION_READY",
        actor_id="advisor_delivery",
        occurred_at=occurred_at or datetime(2026, 5, 20, tzinfo=timezone.utc),
        reason_json=reason_json or {},
        related_version_no=related_version_no,
    )


def test_delivery_summary_uses_latest_execution_status_with_handoff_context():
    requested = _event(
        "EXECUTION_REQUESTED",
        reason_json={
            "execution_request_id": "oms_req_001",
            "execution_provider": "OMS",
        },
        occurred_at=datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc),
    )
    partial = _event(
        "EXECUTION_PARTIALLY_EXECUTED",
        reason_json={
            "execution_request_id": "oms_req_001",
            "execution_provider": "OMS",
            "external_execution_id": "fill_partial_001",
        },
        occurred_at=datetime(2026, 5, 20, 10, 5, tzinfo=timezone.utc),
    )

    summary = build_delivery_summary_from_events([requested, partial])

    assert summary["execution"] == {
        "handoff_status": "PARTIALLY_EXECUTED",
        "execution_request_id": "oms_req_001",
        "execution_provider": "OMS",
        "related_version_no": 1,
        "handoff_requested_at": "2026-05-20T10:00:00+00:00",
        "executed_at": None,
        "latest_event_type": "EXECUTION_PARTIALLY_EXECUTED",
        "external_execution_id": "fill_partial_001",
        "execution_ownership": execution_ownership_boundary(),
    }


def test_delivery_summary_preserves_report_request_projection():
    report = _event(
        "REPORT_REQUESTED",
        reason_json={
            "report_request_id": "prr_001",
            "report_type": "PORTFOLIO_REVIEW",
            "report_service": "lotus-report",
            "status": "READY",
            "report_reference_id": "report_001",
            "artifact_url": "https://lotus-report.local/report_001",
            "include_execution_summary": True,
        },
        occurred_at=datetime(2026, 5, 20, 11, 0, tzinfo=timezone.utc),
    )

    summary = build_delivery_summary_from_events([report])

    assert summary["execution"] is None
    assert summary["reporting"] == {
        "report_request_id": "prr_001",
        "report_type": "PORTFOLIO_REVIEW",
        "report_service": "lotus-report",
        "status": "READY",
        "report_reference_id": "report_001",
        "artifact_url": "https://lotus-report.local/report_001",
        "requested_by": "advisor_delivery",
        "related_version_no": 1,
        "include_execution_summary": True,
        "generated_at": "2026-05-20T11:00:00+00:00",
    }


def test_select_delivery_events_filters_non_delivery_workflow_events():
    events = [
        _event("CREATED"),
        _event("SUBMITTED_FOR_RISK_REVIEW"),
        _event("EXECUTION_REQUESTED"),
        _event("REPORT_REQUESTED"),
    ]

    selected = select_delivery_events(events)

    assert [event.event_type for event in selected] == [
        "EXECUTION_REQUESTED",
        "REPORT_REQUESTED",
    ]


def test_delivery_summary_response_projects_execution_and_reporting_posture():
    events = [
        _event(
            "EXECUTION_REQUESTED",
            reason_json={
                "execution_request_id": "oms_req_001",
                "execution_provider": "OMS",
            },
            occurred_at=datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc),
        ),
        _event(
            "EXECUTED",
            reason_json={
                "execution_request_id": "oms_req_001",
                "execution_provider": "OMS",
                "external_execution_id": "fill_001",
            },
            occurred_at=datetime(2026, 5, 20, 10, 30, tzinfo=timezone.utc),
        ),
        _event(
            "REPORT_REQUESTED",
            reason_json={
                "report_request_id": "prr_001",
                "report_type": "CLIENT_PROPOSAL_SUMMARY",
                "report_service": "lotus-report",
                "status": "READY",
                "report_reference_id": "report_001",
                "include_execution_summary": True,
            },
            occurred_at=datetime(2026, 5, 20, 11, 0, tzinfo=timezone.utc),
        ),
    ]

    response = build_delivery_summary_response(proposal=_proposal(), events=events)

    assert response.execution is not None
    assert response.execution.handoff_status == "EXECUTED"
    assert response.execution.executed_at == "2026-05-20T10:30:00+00:00"
    assert response.execution.execution_ownership == execution_ownership_boundary()
    assert response.reporting is not None
    assert response.reporting.report_type == "CLIENT_PROPOSAL_SUMMARY"
    assert response.explanation == {
        "source": "ADVISORY_WORKFLOW_EVENTS",
        "delivery_projection": "LATEST_EXECUTION_AND_REPORTING_POSTURE",
        "execution_ownership": execution_ownership_boundary(),
    }


def test_delivery_history_response_filters_to_delivery_events():
    events = [
        _event("CREATED"),
        _event("EXECUTION_REQUESTED"),
        _event("REPORT_REQUESTED"),
    ]

    response = build_delivery_history_response(proposal=_proposal(), events=events)

    assert response.event_count == 2
    assert response.latest_event is not None
    assert response.latest_event.event_type == "REPORT_REQUESTED"
    assert [event.event_type for event in response.events] == [
        "EXECUTION_REQUESTED",
        "REPORT_REQUESTED",
    ]
    assert response.explanation == {
        "source": "ADVISORY_WORKFLOW_EVENTS",
        "filter": "DELIVERY_ONLY",
        "execution_ownership": execution_ownership_boundary(),
    }
