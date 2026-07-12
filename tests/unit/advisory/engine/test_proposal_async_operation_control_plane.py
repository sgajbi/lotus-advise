from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.proposals.async_operation_control_plane import (
    ASYNC_OPERATION_CONTROL_CAPABILITY,
    ASYNC_OPERATION_QUARANTINED_CODE,
    AsyncOperationControlFilters,
    AsyncOperationControlPrincipal,
    build_quarantined_async_operation,
    classify_async_operation_for_control,
    evaluate_async_operation_control,
    list_async_operations_for_control,
    normalize_async_operation_control_filters,
)
from src.core.proposals.models import ProposalAsyncOperationRecord
from src.core.proposals.service import ProposalWorkflowService
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository

AS_OF = datetime(2026, 2, 20, 10, 0, tzinfo=timezone.utc)


def test_retry_decision_allows_expired_lease_without_payload_mutation_or_raw_audit_ids() -> None:
    operation = _operation(
        operation_id="pop_expired_retry",
        status="RUNNING",
        attempt_count=1,
        lease_expires_at=AS_OF - timedelta(seconds=1),
    )

    decision = evaluate_async_operation_control(
        operation=operation,
        action="RETRY",
        principal=_authorized_principal(actor_id="operator_123"),
        as_of=AS_OF,
        idempotency_key="control-idem-retry",
        reason="lease expired after worker shutdown",
    )

    assert decision.allowed is True
    assert decision.reason_code == "ASYNC_CONTROL_RETRY_ALLOWED"
    assert decision.control_status == "RECOVERABLE_STUCK"
    assert decision.schedule_execution is True
    assert decision.payload_mutation_allowed is False
    assert "pop_expired_retry" not in str(decision.audit_event)
    assert "operator_123" not in str(decision.audit_event)
    assert decision.audit_event["audit_payload_version"] == (
        "proposal_async_operation_control_decision.v1"
    )


def test_unauthorized_control_decision_fails_closed() -> None:
    decision = evaluate_async_operation_control(
        operation=_operation(operation_id="pop_unauthorized"),
        action="QUARANTINE",
        principal=AsyncOperationControlPrincipal(
            actor_id="advisor_1",
            role="ADVISOR",
            tenant_id="tenant_sg",
            legal_entity_code="SG",
            service_identity="support-console",
            capabilities=frozenset(),
        ),
        as_of=AS_OF,
        idempotency_key="control-idem-denied",
        reason="attempted unsupported operational intervention",
    )

    assert decision.allowed is False
    assert decision.reason_code == "ASYNC_CONTROL_NOT_AUTHORIZED"
    assert decision.schedule_execution is False
    assert decision.target_status is None
    assert decision.payload_mutation_allowed is False


def test_active_lease_blocks_retry_and_quarantine_to_avoid_duplicate_execution() -> None:
    operation = _operation(
        operation_id="pop_active_lease",
        status="RUNNING",
        attempt_count=1,
        lease_expires_at=AS_OF + timedelta(seconds=30),
    )

    retry = evaluate_async_operation_control(
        operation=operation,
        action="RETRY",
        principal=_authorized_principal(),
        as_of=AS_OF,
        idempotency_key="control-idem-active-retry",
        reason="operator retry while worker owns lease",
    )
    quarantine = evaluate_async_operation_control(
        operation=operation,
        action="QUARANTINE",
        principal=_authorized_principal(),
        as_of=AS_OF,
        idempotency_key="control-idem-active-quarantine",
        reason="operator quarantine while worker owns lease",
    )

    assert classify_async_operation_for_control(operation, as_of=AS_OF) == "LEASED"
    assert retry.reason_code == "ASYNC_CONTROL_RETRY_BLOCKED_BY_ACTIVE_LEASE"
    assert quarantine.reason_code == "ASYNC_CONTROL_QUARANTINE_BLOCKED_BY_ACTIVE_LEASE"
    assert retry.allowed is False
    assert quarantine.allowed is False


def test_retry_exhausted_operation_can_be_quarantined_but_not_retried() -> None:
    operation = _operation(
        operation_id="pop_exhausted",
        status="FAILED",
        attempt_count=3,
        max_attempts=3,
        error_json={
            "code": "ProposalLifecycleError",
            "message": "PROPOSAL_ASYNC_ATTEMPTS_EXHAUSTED",
        },
    )

    retry = evaluate_async_operation_control(
        operation=operation,
        action="RETRY",
        principal=_authorized_principal(),
        as_of=AS_OF,
        idempotency_key="control-idem-exhausted-retry",
        reason="operator retry after all attempts exhausted",
    )
    quarantine = evaluate_async_operation_control(
        operation=operation,
        action="QUARANTINE",
        principal=_authorized_principal(),
        as_of=AS_OF,
        idempotency_key="control-idem-exhausted-quarantine",
        reason="operator quarantine after retry exhaustion",
    )

    assert retry.reason_code == "ASYNC_CONTROL_RETRY_BLOCKED_BY_EXHAUSTED_ATTEMPTS"
    assert retry.allowed is False
    assert quarantine.allowed is True
    assert quarantine.target_status == "FAILED"
    assert quarantine.payload_mutation_allowed is False


def test_quarantine_projection_is_idempotent_and_audit_backed() -> None:
    operation = _operation(operation_id="pop_quarantine", status="PENDING")
    decision = evaluate_async_operation_control(
        operation=operation,
        action="QUARANTINE",
        principal=_authorized_principal(),
        as_of=AS_OF,
        idempotency_key="control-idem-quarantine",
        reason="unsupported dependency outage",
    )

    quarantined = build_quarantined_async_operation(
        operation=operation,
        decision=decision,
        finished_at=AS_OF,
    )
    replay_decision = evaluate_async_operation_control(
        operation=quarantined,
        action="QUARANTINE",
        principal=_authorized_principal(),
        as_of=AS_OF,
        idempotency_key="control-idem-quarantine",
        reason="unsupported dependency outage",
    )
    replayed = build_quarantined_async_operation(
        operation=quarantined,
        decision=replay_decision,
        finished_at=AS_OF + timedelta(minutes=1),
    )

    assert quarantined.status == "FAILED"
    assert quarantined.finished_at == AS_OF
    assert quarantined.lease_expires_at is None
    assert quarantined.payload_json == operation.payload_json
    assert quarantined.error_json is not None
    assert quarantined.error_json["code"] == ASYNC_OPERATION_QUARANTINED_CODE
    assert quarantined.error_json["audit_event"]["payload_mutation_allowed"] is False
    assert replay_decision.idempotent_noop is True
    assert replayed == quarantined


def test_control_list_filters_statuses_and_clamps_limit() -> None:
    operations = [
        _operation(operation_id=f"pop_pending_{index}", status="PENDING") for index in range(55)
    ]
    operations.append(
        _operation(
            operation_id="pop_active_lease",
            status="RUNNING",
            lease_expires_at=AS_OF + timedelta(seconds=30),
        )
    )

    filters = normalize_async_operation_control_filters(
        AsyncOperationControlFilters(control_statuses=("PENDING",), limit=99)
    )
    listed = list_async_operations_for_control(
        operations,
        filters=filters,
        as_of=AS_OF,
    )

    assert filters.limit == 50
    assert len(listed) == 50
    assert {item.control_status for item in listed} == {"PENDING"}
    assert "pop_active_lease" not in {item.operation_id for item in listed}


def test_terminal_succeeded_operation_blocks_operator_mutations() -> None:
    operation = _operation(operation_id="pop_succeeded", status="SUCCEEDED")

    retry = evaluate_async_operation_control(
        operation=operation,
        action="RETRY",
        principal=_authorized_principal(),
        as_of=AS_OF,
        idempotency_key="control-idem-terminal-retry",
        reason="operator retry terminal success",
    )
    quarantine = evaluate_async_operation_control(
        operation=operation,
        action="QUARANTINE",
        principal=_authorized_principal(),
        as_of=AS_OF,
        idempotency_key="control-idem-terminal-quarantine",
        reason="operator quarantine terminal success",
    )

    assert retry.allowed is False
    assert quarantine.allowed is False
    assert retry.reason_code == "ASYNC_CONTROL_RETRY_BLOCKED_BY_TERMINAL_STATE"
    assert quarantine.reason_code == "ASYNC_CONTROL_QUARANTINE_BLOCKED_BY_TERMINAL_STATE"


def test_service_lists_control_candidates_and_persists_quarantine_decision() -> None:
    repository = InMemoryProposalRepository()
    repository.create_operation(_operation(operation_id="pop_service_pending", status="PENDING"))
    repository.create_operation(
        _operation(operation_id="pop_service_succeeded", status="SUCCEEDED")
    )
    service = ProposalWorkflowService(repository=repository)

    listed = service.list_async_operations_for_control(
        filters=AsyncOperationControlFilters(control_statuses=("PENDING",))
    )
    decision = service.quarantine_async_operation(
        operation_id="pop_service_pending",
        principal=_authorized_principal(),
        idempotency_key="control-idem-service-quarantine",
        reason="operator quarantine from service boundary",
    )
    stored = repository.get_operation(operation_id="pop_service_pending")
    relisted = service.list_async_operations_for_control(
        filters=AsyncOperationControlFilters(control_statuses=("QUARANTINED",))
    )

    assert [item.operation_id for item in listed] == ["pop_service_pending"]
    assert decision.allowed is True
    assert stored is not None
    assert stored.status == "FAILED"
    assert stored.error_json is not None
    assert stored.error_json["code"] == ASYNC_OPERATION_QUARANTINED_CODE
    assert [item.operation_id for item in relisted] == ["pop_service_pending"]


def _authorized_principal(actor_id: str = "operations_user") -> AsyncOperationControlPrincipal:
    return AsyncOperationControlPrincipal(
        actor_id=actor_id,
        role="OPERATIONS",
        tenant_id="tenant_sg",
        legal_entity_code="SG",
        service_identity="support-console",
        capabilities=frozenset({ASYNC_OPERATION_CONTROL_CAPABILITY}),
    )


def _operation(
    *,
    operation_id: str,
    status: str = "PENDING",
    attempt_count: int = 0,
    max_attempts: int = 3,
    lease_expires_at: datetime | None = None,
    error_json: dict[str, object] | None = None,
) -> ProposalAsyncOperationRecord:
    return ProposalAsyncOperationRecord(
        operation_id=operation_id,
        operation_type="CREATE_PROPOSAL",
        status=status,
        correlation_id=f"corr_{operation_id}",
        idempotency_key=f"idem_{operation_id}",
        proposal_id=None,
        created_by="advisor_1",
        created_at=AS_OF - timedelta(minutes=10),
        payload_json={"payload": {"portfolio_id": "pf_001"}},
        attempt_count=attempt_count,
        max_attempts=max_attempts,
        started_at=(AS_OF - timedelta(minutes=2) if status == "RUNNING" else None),
        lease_expires_at=lease_expires_at,
        finished_at=(AS_OF - timedelta(minutes=1) if status in {"SUCCEEDED", "FAILED"} else None),
        result_json=None,
        error_json=error_json,
    )
