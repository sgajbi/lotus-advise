from datetime import datetime, timezone

from src.core.proposals.execution_update import build_execution_update_event
from src.core.proposals.models import ProposalExecutionUpdateRequest


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
