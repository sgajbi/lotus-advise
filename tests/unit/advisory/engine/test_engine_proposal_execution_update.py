from datetime import datetime, timezone

from src.core.proposals.execution_update import (
    ProposalExecutionUpdateProviderMismatchError,
    ProposalExecutionUpdateRequestIdMismatchError,
    ProposalExecutionUpdateTerminalStateError,
    ProposalExecutionUpdateTimestampError,
    apply_execution_update_state,
    build_execution_update_event,
    build_execution_update_idempotency_key,
    resolve_execution_update_occurred_at,
    validate_execution_update_handoff_identity,
    validate_execution_update_occurred_after_handoff,
    validate_execution_update_state,
)
from src.core.proposals.models import (
    ProposalExecutionUpdateRequest,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)


def _payload(**overrides) -> ProposalExecutionUpdateRequest:
    values = {
        "update_id": "exec_update_001",
        "actor_id": "lotus-manage",
        "execution_request_id": "pex_execution_update",
        "execution_provider": "lotus-manage",
        "update_status": "PARTIALLY_EXECUTED",
        "related_version_no": None,
        "external_execution_id": "oms_fill_001",
        "occurred_at": None,
        "details": {"filled_quantity": "50", "remaining_quantity": "25"},
    }
    values.update(overrides)
    return ProposalExecutionUpdateRequest(**values)


def _proposal() -> ProposalRecord:
    created_at = datetime(2026, 5, 21, 9, 0, tzinfo=timezone.utc)
    return ProposalRecord(
        proposal_id="pp_execution_update",
        portfolio_id="pf_execution_update",
        mandate_id="mandate_execution_update",
        jurisdiction="SG",
        created_by="advisor_execution_update",
        created_at=created_at,
        last_event_at=created_at,
        current_state="EXECUTION_READY",
        current_version_no=3,
        title="Execution update state",
        advisor_notes=None,
        lifecycle_origin="DIRECT_CREATE",
        source_workspace_id=None,
    )


def test_build_execution_update_event_preserves_reconciliation_payload():
    event = build_execution_update_event(
        event_id="pwe_execution_update",
        proposal_id="pp_execution_update",
        current_state="EXECUTION_READY",
        payload=_payload(related_version_no=4),
        event_type="EXECUTION_PARTIALLY_EXECUTED",
        to_state="EXECUTION_READY",
        occurred_at=datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc),
        request_hash="sha256:update",
        handoff_related_version_no=3,
    )

    assert event.event_type == "EXECUTION_PARTIALLY_EXECUTED"
    assert event.from_state == "EXECUTION_READY"
    assert event.to_state == "EXECUTION_READY"
    assert event.actor_id == "lotus-manage"
    assert event.related_version_no == 4
    assert event.reason_json == {
        "update_id": "exec_update_001",
        "execution_request_id": "pex_execution_update",
        "execution_provider": "lotus-manage",
        "external_execution_id": "oms_fill_001",
        "details": {"filled_quantity": "50", "remaining_quantity": "25"},
        "idempotency_key": "execution-update:exec_update_001",
        "idempotency_request_hash": "sha256:update",
    }


def test_build_execution_update_event_defaults_to_handoff_version_and_omits_nulls():
    event = build_execution_update_event(
        event_id="pwe_execution_update",
        proposal_id="pp_execution_update",
        current_state="EXECUTION_READY",
        payload=_payload(
            update_status="EXECUTED",
            related_version_no=None,
            external_execution_id=None,
            details={},
        ),
        event_type="EXECUTED",
        to_state="EXECUTED",
        occurred_at=datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc),
        request_hash="sha256:update",
        handoff_related_version_no=3,
    )

    assert event.related_version_no == 3
    assert event.reason_json == {
        "update_id": "exec_update_001",
        "execution_request_id": "pex_execution_update",
        "execution_provider": "lotus-manage",
        "details": {},
        "idempotency_key": "execution-update:exec_update_001",
        "idempotency_request_hash": "sha256:update",
    }


def test_build_execution_update_idempotency_key_uses_update_identity():
    assert (
        build_execution_update_idempotency_key(payload=_payload(update_id="exec_update_987"))
        == "execution-update:exec_update_987"
    )


def test_validate_execution_update_handoff_identity_accepts_matching_identity():
    handoff_event = ProposalWorkflowEventRecord(
        event_id="pwe_execution_requested",
        proposal_id="pp_execution_update",
        event_type="EXECUTION_REQUESTED",
        from_state="EXECUTION_READY",
        to_state="EXECUTION_READY",
        actor_id="advisor_execution_update",
        occurred_at=datetime(2026, 5, 21, 9, 55, tzinfo=timezone.utc),
        reason_json={
            "execution_request_id": "pex_execution_update",
            "execution_provider": "lotus-manage",
        },
        related_version_no=3,
    )

    validate_execution_update_handoff_identity(
        handoff_event=handoff_event,
        payload=_payload(),
    )


def test_validate_execution_update_handoff_identity_rejects_request_id_mismatch():
    handoff_event = ProposalWorkflowEventRecord(
        event_id="pwe_execution_requested",
        proposal_id="pp_execution_update",
        event_type="EXECUTION_REQUESTED",
        from_state="EXECUTION_READY",
        to_state="EXECUTION_READY",
        actor_id="advisor_execution_update",
        occurred_at=datetime(2026, 5, 21, 9, 55, tzinfo=timezone.utc),
        reason_json={
            "execution_request_id": "pex_other",
            "execution_provider": "lotus-manage",
        },
        related_version_no=3,
    )

    try:
        validate_execution_update_handoff_identity(
            handoff_event=handoff_event,
            payload=_payload(),
        )
    except ProposalExecutionUpdateRequestIdMismatchError as exc:
        assert str(exc) == "EXECUTION_REQUEST_ID_MISMATCH"
    else:
        raise AssertionError("expected execution request ID mismatch")


def test_validate_execution_update_handoff_identity_rejects_provider_mismatch():
    handoff_event = ProposalWorkflowEventRecord(
        event_id="pwe_execution_requested",
        proposal_id="pp_execution_update",
        event_type="EXECUTION_REQUESTED",
        from_state="EXECUTION_READY",
        to_state="EXECUTION_READY",
        actor_id="advisor_execution_update",
        occurred_at=datetime(2026, 5, 21, 9, 55, tzinfo=timezone.utc),
        reason_json={
            "execution_request_id": "pex_execution_update",
            "execution_provider": "external-oms",
        },
        related_version_no=3,
    )

    try:
        validate_execution_update_handoff_identity(
            handoff_event=handoff_event,
            payload=_payload(),
        )
    except ProposalExecutionUpdateProviderMismatchError as exc:
        assert str(exc) == "EXECUTION_PROVIDER_MISMATCH"
    else:
        raise AssertionError("expected execution provider mismatch")


def test_validate_execution_update_state_accepts_non_terminal_state():
    validate_execution_update_state(
        proposal=_proposal(),
        terminal_states={"EXECUTED", "CANCELLED"},
    )


def test_validate_execution_update_state_rejects_terminal_state():
    proposal = _proposal()
    proposal.current_state = "EXECUTED"

    try:
        validate_execution_update_state(
            proposal=proposal,
            terminal_states={"EXECUTED", "CANCELLED"},
        )
    except ProposalExecutionUpdateTerminalStateError as exc:
        assert str(exc) == "PROPOSAL_TERMINAL_STATE: execution update rejected"
    else:
        raise AssertionError("expected execution update terminal state error")


def test_validate_execution_update_occurred_after_handoff_accepts_equal_or_later_timestamp():
    handoff_event = ProposalWorkflowEventRecord(
        event_id="pwe_execution_requested",
        proposal_id="pp_execution_update",
        event_type="EXECUTION_REQUESTED",
        from_state="EXECUTION_READY",
        to_state="EXECUTION_READY",
        actor_id="advisor_execution_update",
        occurred_at=datetime(2026, 5, 21, 9, 55, tzinfo=timezone.utc),
        reason_json={"execution_request_id": "pex_execution_update"},
        related_version_no=3,
    )

    validate_execution_update_occurred_after_handoff(
        occurred_at=handoff_event.occurred_at,
        handoff_event=handoff_event,
    )
    validate_execution_update_occurred_after_handoff(
        occurred_at=datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc),
        handoff_event=handoff_event,
    )


def test_validate_execution_update_occurred_after_handoff_rejects_earlier_timestamp():
    handoff_event = ProposalWorkflowEventRecord(
        event_id="pwe_execution_requested",
        proposal_id="pp_execution_update",
        event_type="EXECUTION_REQUESTED",
        from_state="EXECUTION_READY",
        to_state="EXECUTION_READY",
        actor_id="advisor_execution_update",
        occurred_at=datetime(2026, 5, 21, 9, 55, tzinfo=timezone.utc),
        reason_json={"execution_request_id": "pex_execution_update"},
        related_version_no=3,
    )

    try:
        validate_execution_update_occurred_after_handoff(
            occurred_at=datetime(2026, 5, 21, 9, 54, 59, tzinfo=timezone.utc),
            handoff_event=handoff_event,
        )
    except ProposalExecutionUpdateTimestampError as exc:
        assert str(exc) == "EXECUTION_UPDATE_OCCURRED_BEFORE_HANDOFF"
    else:
        raise AssertionError("expected execution update timestamp error")


def test_resolve_execution_update_occurred_at_prefers_payload_timestamp():
    resolved = resolve_execution_update_occurred_at(
        payload=_payload(occurred_at="2026-05-21T10:15:00+00:00"),
        default_occurred_at=datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc),
    )

    assert resolved == datetime(2026, 5, 21, 10, 15, tzinfo=timezone.utc)


def test_resolve_execution_update_occurred_at_uses_default_when_payload_omits_timestamp():
    default_occurred_at = datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc)

    resolved = resolve_execution_update_occurred_at(
        payload=_payload(occurred_at=None),
        default_occurred_at=default_occurred_at,
    )

    assert resolved == default_occurred_at


def test_apply_execution_update_state_updates_state_and_event_timestamp():
    proposal = _proposal()
    event = ProposalWorkflowEventRecord(
        event_id="pwe_execution_update",
        proposal_id=proposal.proposal_id,
        event_type="EXECUTED",
        from_state="EXECUTION_READY",
        to_state="EXECUTED",
        actor_id="lotus-manage",
        occurred_at=datetime(2026, 5, 21, 10, 5, tzinfo=timezone.utc),
        reason_json={"execution_request_id": "pex_execution_update"},
        related_version_no=3,
    )

    apply_execution_update_state(
        proposal=proposal,
        to_state="EXECUTED",
        event=event,
    )

    assert proposal.current_state == "EXECUTED"
    assert proposal.last_event_at == event.occurred_at
