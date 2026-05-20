from datetime import datetime, timezone

from src.core.proposals.lifecycle_events import (
    build_state_transition_event,
    build_state_transition_response,
)
from src.core.proposals.models import (
    ProposalRecord,
    ProposalStateTransitionRequest,
    ProposalWorkflowEventRecord,
)


def _proposal() -> ProposalRecord:
    return ProposalRecord(
        proposal_id="pp_lifecycle_events",
        portfolio_id="pf_lifecycle_events",
        mandate_id="mandate_lifecycle_events",
        jurisdiction="SG",
        created_by="advisor_lifecycle",
        created_at=datetime(2026, 5, 21, 9, 0, tzinfo=timezone.utc),
        last_event_at=datetime(2026, 5, 21, 9, 5, tzinfo=timezone.utc),
        current_state="DRAFT",
        current_version_no=2,
        title="Lifecycle event test",
        lifecycle_origin="DIRECT_CREATE",
        source_workspace_id=None,
    )


def _transition_request(**overrides) -> ProposalStateTransitionRequest:
    values = {
        "event_type": "SUBMITTED_FOR_COMPLIANCE_REVIEW",
        "actor_id": "advisor_lifecycle",
        "related_version_no": 2,
        "reason": {"comment": "Requires compliance review"},
        "expected_state": "DRAFT",
    }
    values.update(overrides)
    return ProposalStateTransitionRequest(**values)


def test_build_state_transition_event_preserves_reason_and_idempotency_metadata():
    event = build_state_transition_event(
        event_id="pwe_lifecycle",
        proposal=_proposal(),
        payload=_transition_request(),
        to_state="COMPLIANCE_REVIEW",
        occurred_at=datetime(2026, 5, 21, 9, 10, tzinfo=timezone.utc),
        idempotency_key="idem_lifecycle",
        request_hash="sha256:lifecycle",
    )

    assert event.event_type == "SUBMITTED_FOR_COMPLIANCE_REVIEW"
    assert event.from_state == "DRAFT"
    assert event.to_state == "COMPLIANCE_REVIEW"
    assert event.actor_id == "advisor_lifecycle"
    assert event.related_version_no == 2
    assert event.reason_json == {
        "comment": "Requires compliance review",
        "idempotency_key": "idem_lifecycle",
        "idempotency_request_hash": "sha256:lifecycle",
    }


def test_build_state_transition_response_projects_latest_event():
    event = ProposalWorkflowEventRecord(
        event_id="pwe_lifecycle",
        proposal_id="pp_lifecycle_events",
        event_type="SUBMITTED_FOR_RISK_REVIEW",
        from_state="DRAFT",
        to_state="RISK_REVIEW",
        actor_id="advisor_lifecycle",
        occurred_at=datetime(2026, 5, 21, 9, 10, tzinfo=timezone.utc),
        reason_json={"comment": "Risk review"},
        related_version_no=2,
    )

    response = build_state_transition_response(
        proposal_id="pp_lifecycle_events",
        current_state="RISK_REVIEW",
        event=event,
    )

    assert response.proposal_id == "pp_lifecycle_events"
    assert response.current_state == "RISK_REVIEW"
    assert response.latest_workflow_event.event_id == "pwe_lifecycle"
    assert response.latest_workflow_event.reason == {"comment": "Risk review"}
    assert response.approval is None
