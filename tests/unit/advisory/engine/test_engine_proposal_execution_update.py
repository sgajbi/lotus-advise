from datetime import datetime, timezone

from src.core.proposals.execution_update import (
    ProposalExecutionUpdateProviderMismatchError,
    ProposalExecutionUpdateRequestIdMismatchError,
    ProposalExecutionUpdateTerminalStateError,
    ProposalExecutionUpdateTimestampError,
    apply_execution_update_state,
    build_execution_update_event,
    build_execution_update_event_and_apply_state,
    build_execution_update_idempotency_key,
    build_execution_update_request_hash,
    find_replayed_execution_update_event,
    resolve_execution_update_occurred_at,
    validate_execution_update_handoff_identity,
    validate_execution_update_occurred_after_handoff,
    validate_execution_update_state,
)
from src.core.proposals.execution_update_command import record_proposal_execution_update
from src.core.proposals.idempotency import ProposalReplayHashConflictError
from src.core.proposals.models import (
    ProposalExecutionUpdateRequest,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


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


def test_build_execution_update_event_isolates_nested_details():
    payload = _payload(details={"fill": {"quantity": "50"}})

    event = build_execution_update_event(
        event_id="pwe_execution_update_immutable",
        proposal_id="pp_execution_update",
        current_state="EXECUTION_READY",
        payload=payload,
        event_type="EXECUTION_PARTIALLY_EXECUTED",
        to_state="EXECUTION_READY",
        occurred_at=datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc),
        request_hash="sha256:update",
        handoff_related_version_no=3,
    )

    payload.details["fill"]["quantity"] = "999"

    assert event.reason_json["details"] == {"fill": {"quantity": "50"}}


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


def test_build_execution_update_request_hash_is_canonical_and_payload_sensitive():
    first_hash = build_execution_update_request_hash(
        payload=_payload(details={"remaining_quantity": "25", "filled_quantity": "50"})
    )
    reordered_hash = build_execution_update_request_hash(
        payload=_payload(details={"filled_quantity": "50", "remaining_quantity": "25"})
    )
    changed_hash = build_execution_update_request_hash(
        payload=_payload(details={"filled_quantity": "75", "remaining_quantity": "0"})
    )

    assert first_hash.startswith("sha256:")
    assert first_hash == reordered_hash
    assert first_hash != changed_hash


def test_find_replayed_execution_update_event_uses_update_identity_and_hash():
    payload = _payload(update_id="exec_update_replay")
    request_hash = build_execution_update_request_hash(payload=payload)
    event = ProposalWorkflowEventRecord(
        event_id="pwe_execution_update_replay",
        proposal_id="pp_execution_update",
        event_type="EXECUTION_PARTIALLY_EXECUTED",
        from_state="EXECUTION_READY",
        to_state="EXECUTION_READY",
        actor_id="lotus-manage",
        occurred_at=datetime(2026, 5, 21, 10, 5, tzinfo=timezone.utc),
        reason_json={
            "idempotency_key": "execution-update:exec_update_replay",
            "idempotency_request_hash": request_hash,
        },
        related_version_no=3,
    )

    replay = find_replayed_execution_update_event(
        events=[event],
        payload=payload,
        request_hash=request_hash,
    )

    assert replay == event


def test_find_replayed_execution_update_event_rejects_hash_conflict():
    payload = _payload(update_id="exec_update_replay")
    event = ProposalWorkflowEventRecord(
        event_id="pwe_execution_update_replay",
        proposal_id="pp_execution_update",
        event_type="EXECUTION_PARTIALLY_EXECUTED",
        from_state="EXECUTION_READY",
        to_state="EXECUTION_READY",
        actor_id="lotus-manage",
        occurred_at=datetime(2026, 5, 21, 10, 5, tzinfo=timezone.utc),
        reason_json={
            "idempotency_key": "execution-update:exec_update_replay",
            "idempotency_request_hash": "sha256:original",
        },
        related_version_no=3,
    )

    try:
        find_replayed_execution_update_event(
            events=[event],
            payload=payload,
            request_hash="sha256:changed",
        )
    except ProposalReplayHashConflictError as exc:
        assert str(exc) == "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"
    else:
        raise AssertionError("expected execution update replay hash conflict")


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


def test_build_execution_update_event_and_apply_state_returns_event_and_updates_state():
    proposal = _proposal()
    occurred_at = datetime(2026, 5, 21, 10, 5, tzinfo=timezone.utc)

    event = build_execution_update_event_and_apply_state(
        event_id="pwe_execution_update",
        proposal=proposal,
        payload=_payload(update_status="EXECUTED", related_version_no=None),
        event_type="EXECUTED",
        to_state="EXECUTED",
        occurred_at=occurred_at,
        request_hash="sha256:update",
        handoff_related_version_no=3,
    )

    assert event.proposal_id == proposal.proposal_id
    assert event.from_state == "EXECUTION_READY"
    assert event.to_state == "EXECUTED"
    assert event.related_version_no == 3
    assert proposal.current_state == "EXECUTED"
    assert proposal.last_event_at == occurred_at


def test_record_proposal_execution_update_persists_state_and_handoff_lineage():
    repository = InMemoryProposalRepository()
    proposal = _proposal()
    handoff_at = datetime(2026, 5, 21, 9, 55, tzinfo=timezone.utc)
    update_at = datetime(2026, 5, 21, 10, 5, tzinfo=timezone.utc)
    repository.create_proposal(proposal)
    repository.append_event(
        ProposalWorkflowEventRecord(
            event_id="pwe_execution_requested",
            proposal_id=proposal.proposal_id,
            event_type="EXECUTION_REQUESTED",
            from_state="EXECUTION_READY",
            to_state="EXECUTION_READY",
            actor_id="advisor_execution_update",
            occurred_at=handoff_at,
            reason_json={
                "execution_request_id": "pex_execution_update",
                "execution_provider": "lotus-manage",
            },
            related_version_no=3,
        )
    )

    response = record_proposal_execution_update(
        repository=repository,
        proposal_id=proposal.proposal_id,
        payload=_payload(update_status="EXECUTED", occurred_at=update_at.isoformat()),
        terminal_states={"EXECUTED", "CANCELLED"},
        default_occurred_at=datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc),
    )

    persisted_proposal = repository.get_proposal(proposal_id=proposal.proposal_id)
    events = repository.list_events(proposal_id=proposal.proposal_id)
    execution_update = events[-1]

    assert response is None
    assert persisted_proposal is not None
    assert persisted_proposal.current_state == "EXECUTED"
    assert persisted_proposal.last_event_at == update_at
    assert execution_update.event_type == "EXECUTED"
    assert execution_update.related_version_no == 3
    assert execution_update.reason_json["idempotency_key"] == "execution-update:exec_update_001"
    assert execution_update.reason_json["idempotency_request_hash"].startswith("sha256:")
