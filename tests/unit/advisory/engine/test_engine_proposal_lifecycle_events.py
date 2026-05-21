from datetime import datetime, timezone

from src.core.proposals.lifecycle_events import (
    apply_lifecycle_transition_state,
    build_approval_record,
    build_approval_request_hash,
    build_approval_transition_event,
    build_approval_transition_response,
    build_new_version_created_event,
    build_proposal_created_event,
    build_state_transition_event,
    build_state_transition_request_hash,
    build_state_transition_response,
)
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalApprovalRequest,
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


def test_build_proposal_created_event_uses_draft_lifecycle_origin():
    event = build_proposal_created_event(
        event_id="pwe_created",
        proposal_id="pp_lifecycle_events",
        actor_id="advisor_lifecycle",
        occurred_at=datetime(2026, 5, 21, 9, 6, tzinfo=timezone.utc),
        related_version_no=1,
        correlation_id="corr_created",
    )

    assert event.event_type == "CREATED"
    assert event.from_state is None
    assert event.to_state == "DRAFT"
    assert event.actor_id == "advisor_lifecycle"
    assert event.reason_json == {"correlation_id": "corr_created"}
    assert event.related_version_no == 1


def test_build_new_version_created_event_resets_to_draft_and_preserves_prior_state():
    proposal = _proposal()
    proposal.current_state = "EXECUTION_READY"

    event = build_new_version_created_event(
        event_id="pwe_new_version",
        proposal=proposal,
        actor_id="advisor_lifecycle",
        occurred_at=datetime(2026, 5, 21, 9, 7, tzinfo=timezone.utc),
        related_version_no=3,
        correlation_id=None,
    )

    assert event.event_type == "NEW_VERSION_CREATED"
    assert event.from_state == "EXECUTION_READY"
    assert event.to_state == "DRAFT"
    assert event.reason_json == {}
    assert event.related_version_no == 3


def _approval_request(**overrides) -> ProposalApprovalRequest:
    values = {
        "approval_type": "CLIENT_CONSENT",
        "approved": True,
        "actor_id": "client_lifecycle",
        "related_version_no": 2,
        "details": {"channel": "IN_PERSON"},
        "expected_state": "AWAITING_CLIENT_CONSENT",
    }
    values.update(overrides)
    return ProposalApprovalRequest(**values)


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


def test_build_state_transition_request_hash_is_canonical_and_reason_sensitive():
    first_hash = build_state_transition_request_hash(
        payload=_transition_request(reason={"b": "second", "a": "first"})
    )
    reordered_hash = build_state_transition_request_hash(
        payload=_transition_request(reason={"a": "first", "b": "second"})
    )
    changed_hash = build_state_transition_request_hash(
        payload=_transition_request(reason={"a": "first", "b": "changed"})
    )

    assert first_hash.startswith("sha256:")
    assert first_hash == reordered_hash
    assert first_hash != changed_hash


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


def test_apply_lifecycle_transition_state_updates_state_and_event_timestamp():
    proposal = _proposal()
    event = ProposalWorkflowEventRecord(
        event_id="pwe_apply_lifecycle",
        proposal_id=proposal.proposal_id,
        event_type="SUBMITTED_FOR_RISK_REVIEW",
        from_state="DRAFT",
        to_state="RISK_REVIEW",
        actor_id="advisor_lifecycle",
        occurred_at=datetime(2026, 5, 21, 9, 11, tzinfo=timezone.utc),
        reason_json={"comment": "Risk review"},
        related_version_no=2,
    )

    apply_lifecycle_transition_state(
        proposal=proposal,
        to_state="RISK_REVIEW",
        event=event,
    )

    assert proposal.current_state == "RISK_REVIEW"
    assert proposal.last_event_at == event.occurred_at


def test_build_approval_record_preserves_details_and_idempotency_metadata():
    approval = build_approval_record(
        approval_id="pap_lifecycle",
        proposal_id="pp_lifecycle_events",
        payload=_approval_request(),
        occurred_at=datetime(2026, 5, 21, 9, 12, tzinfo=timezone.utc),
        idempotency_key="idem_approval",
        request_hash="sha256:approval",
    )

    assert approval.approval_type == "CLIENT_CONSENT"
    assert approval.approved is True
    assert approval.actor_id == "client_lifecycle"
    assert approval.related_version_no == 2
    assert approval.details_json == {
        "channel": "IN_PERSON",
        "idempotency_key": "idem_approval",
        "idempotency_request_hash": "sha256:approval",
    }


def test_build_approval_request_hash_is_canonical_and_details_sensitive():
    first_hash = build_approval_request_hash(
        payload=_approval_request(details={"b": "second", "a": "first"})
    )
    reordered_hash = build_approval_request_hash(
        payload=_approval_request(details={"a": "first", "b": "second"})
    )
    changed_hash = build_approval_request_hash(
        payload=_approval_request(details={"a": "first", "b": "changed"})
    )

    assert first_hash.startswith("sha256:")
    assert first_hash == reordered_hash
    assert first_hash != changed_hash


def test_build_approval_transition_event_matches_approval_audit_payload():
    proposal = _proposal()
    proposal.current_state = "AWAITING_CLIENT_CONSENT"
    event = build_approval_transition_event(
        event_id="pwe_approval",
        proposal=proposal,
        payload=_approval_request(),
        event_type="CLIENT_CONSENT_RECORDED",
        to_state="EXECUTION_READY",
        occurred_at=datetime(2026, 5, 21, 9, 12, tzinfo=timezone.utc),
        idempotency_key="idem_approval",
        request_hash="sha256:approval",
    )

    assert event.event_type == "CLIENT_CONSENT_RECORDED"
    assert event.from_state == "AWAITING_CLIENT_CONSENT"
    assert event.to_state == "EXECUTION_READY"
    assert event.actor_id == "client_lifecycle"
    assert event.related_version_no == 2
    assert event.reason_json == {
        "channel": "IN_PERSON",
        "idempotency_key": "idem_approval",
        "idempotency_request_hash": "sha256:approval",
    }


def test_build_approval_transition_response_projects_approval_record():
    event = ProposalWorkflowEventRecord(
        event_id="pwe_approval",
        proposal_id="pp_lifecycle_events",
        event_type="CLIENT_CONSENT_RECORDED",
        from_state="AWAITING_CLIENT_CONSENT",
        to_state="EXECUTION_READY",
        actor_id="client_lifecycle",
        occurred_at=datetime(2026, 5, 21, 9, 12, tzinfo=timezone.utc),
        reason_json={"channel": "IN_PERSON"},
        related_version_no=2,
    )
    approval = ProposalApprovalRecordData(
        approval_id="pap_lifecycle",
        proposal_id="pp_lifecycle_events",
        approval_type="CLIENT_CONSENT",
        approved=True,
        actor_id="client_lifecycle",
        occurred_at=datetime(2026, 5, 21, 9, 12, tzinfo=timezone.utc),
        details_json={"channel": "IN_PERSON"},
        related_version_no=2,
    )

    response = build_approval_transition_response(
        proposal_id="pp_lifecycle_events",
        current_state="EXECUTION_READY",
        event=event,
        approval=approval,
    )

    assert response.current_state == "EXECUTION_READY"
    assert response.latest_workflow_event.event_type == "CLIENT_CONSENT_RECORDED"
    assert response.approval is not None
    assert response.approval.approval_id == "pap_lifecycle"
    assert response.approval.details == {"channel": "IN_PERSON"}
