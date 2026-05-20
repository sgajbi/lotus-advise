from datetime import datetime, timezone

from src.core.proposals.async_operations import (
    apply_runtime_exception_outcome,
    begin_async_attempt,
    build_async_replay_lineage,
    build_create_proposal_async_operation,
    build_create_version_async_operation,
    extract_async_result_version_no,
    mark_operation_failed,
    mark_operation_succeeded,
)
from src.core.proposals.models import (
    ProposalAsyncOperationRecord,
    ProposalCreateRequest,
    ProposalCreateResponse,
    ProposalSummary,
    ProposalVersionDetail,
    ProposalVersionRequest,
    ProposalWorkflowEvent,
)


def _operation(*, attempt_count: int = 0, max_attempts: int = 3) -> ProposalAsyncOperationRecord:
    return ProposalAsyncOperationRecord(
        operation_id="pop_async_state",
        operation_type="CREATE_PROPOSAL",
        status="PENDING",
        correlation_id="corr_async_state",
        idempotency_key="idem_async_state",
        proposal_id=None,
        created_by="advisor_async_state",
        created_at=datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc),
        payload_json={"payload": {"created_by": "advisor_async_state"}},
        attempt_count=attempt_count,
        max_attempts=max_attempts,
    )


def _response() -> ProposalCreateResponse:
    return ProposalCreateResponse.model_construct(
        proposal=ProposalSummary(
            proposal_id="pp_async_state",
            portfolio_id="pf_async_state",
            mandate_id="mandate_async_state",
            jurisdiction="SG",
            created_by="advisor_async_state",
            created_at="2026-05-20T09:00:00+00:00",
            last_event_at="2026-05-20T09:01:00+00:00",
            current_state="DRAFT",
            current_version_no=1,
            title="Async state proposal",
            lifecycle_origin="DIRECT_CREATE",
            source_workspace_id=None,
        ),
        version=ProposalVersionDetail.model_construct(
            proposal_version_id="ppv_async_state",
            proposal_id="pp_async_state",
            version_no=1,
            created_at="2026-05-20T09:01:00+00:00",
            request_hash="sha256:req",
            artifact_hash="sha256:artifact",
            simulation_hash="sha256:simulation",
            status_at_creation="READY",
            proposal_result={"status": "READY"},
            artifact={},
            evidence_bundle={},
            gate_decision=None,
        ),
        latest_workflow_event=ProposalWorkflowEvent(
            event_id="pwe_async_state",
            proposal_id="pp_async_state",
            event_type="CREATED",
            from_state=None,
            to_state="DRAFT",
            actor_id="advisor_async_state",
            occurred_at="2026-05-20T09:01:00+00:00",
            reason={},
            related_version_no=1,
        ),
    )


def _simulate_request(portfolio_id: str = "pf_async_state") -> dict:
    return {
        "portfolio_snapshot": {
            "portfolio_id": portfolio_id,
            "base_currency": "USD",
            "positions": [{"instrument_id": "EQ_OLD", "quantity": "10"}],
            "cash_balances": [{"currency": "USD", "amount": "1000"}],
        },
        "market_data_snapshot": {
            "prices": [
                {"instrument_id": "EQ_OLD", "price": "100", "currency": "USD"},
                {"instrument_id": "EQ_NEW", "price": "50", "currency": "USD"},
            ],
            "fx_rates": [],
        },
        "shelf_entries": [
            {"instrument_id": "EQ_OLD", "status": "APPROVED"},
            {"instrument_id": "EQ_NEW", "status": "APPROVED"},
        ],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [{"currency": "USD", "amount": "100"}],
        "proposed_trades": [{"side": "BUY", "instrument_id": "EQ_NEW", "quantity": "2"}],
    }


def test_build_create_proposal_async_operation_preserves_submission_identity():
    created_at = datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc)
    payload = ProposalCreateRequest(
        created_by="advisor_async_state",
        simulate_request=_simulate_request(),
        metadata={"title": "Async state proposal"},
    )

    operation = build_create_proposal_async_operation(
        operation_id="pop_create_async",
        correlation_id="corr_create_async",
        idempotency_key="idem_create_async",
        payload=payload,
        submission_hash="sha256:create-submission",
        created_at=created_at,
        max_attempts=3,
    )

    assert operation.operation_id == "pop_create_async"
    assert operation.operation_type == "CREATE_PROPOSAL"
    assert operation.status == "PENDING"
    assert operation.correlation_id == "corr_create_async"
    assert operation.idempotency_key == "idem_create_async"
    assert operation.proposal_id is None
    assert operation.created_by == "advisor_async_state"
    assert operation.created_at == created_at
    assert operation.payload_json["idempotency_key"] == "idem_create_async"
    assert operation.payload_json["submission_hash"] == "sha256:create-submission"
    assert operation.payload_json["payload"]["metadata"]["title"] == "Async state proposal"
    assert operation.attempt_count == 0
    assert operation.max_attempts == 3
    assert operation.started_at is None
    assert operation.finished_at is None
    assert operation.result_json is None
    assert operation.error_json is None


def test_build_create_version_async_operation_scopes_replay_to_proposal():
    created_at = datetime(2026, 5, 20, 9, 1, tzinfo=timezone.utc)
    payload = ProposalVersionRequest(
        created_by="advisor_async_state",
        simulate_request=_simulate_request(portfolio_id="pf_async_version"),
    )

    operation = build_create_version_async_operation(
        operation_id="pop_version_async",
        proposal_id="pp_async_version",
        correlation_id="corr_version_async",
        payload=payload,
        submission_hash="sha256:version-submission",
        created_at=created_at,
        max_attempts=4,
    )

    assert operation.operation_id == "pop_version_async"
    assert operation.operation_type == "CREATE_PROPOSAL_VERSION"
    assert operation.status == "PENDING"
    assert operation.correlation_id == "corr_version_async"
    assert operation.idempotency_key is None
    assert operation.proposal_id == "pp_async_version"
    assert operation.created_by == "advisor_async_state"
    assert operation.created_at == created_at
    assert operation.payload_json["proposal_id"] == "pp_async_version"
    assert operation.payload_json["submission_hash"] == "sha256:version-submission"
    assert operation.payload_json["payload"]["created_by"] == "advisor_async_state"
    assert operation.attempt_count == 0
    assert operation.max_attempts == 4
    assert operation.started_at is None
    assert operation.finished_at is None
    assert operation.result_json is None
    assert operation.error_json is None


def test_begin_async_attempt_sets_running_state_and_lease():
    operation = _operation()
    started_at = datetime(2026, 5, 20, 9, 2, tzinfo=timezone.utc)

    begin_async_attempt(
        operation=operation,
        attempt_started_at=started_at,
        lease_seconds=60,
    )

    assert operation.status == "RUNNING"
    assert operation.attempt_count == 1
    assert operation.started_at == started_at
    assert operation.lease_expires_at == datetime(2026, 5, 20, 9, 3, tzinfo=timezone.utc)
    assert operation.finished_at is None
    assert operation.result_json is None
    assert operation.error_json is None


def test_mark_operation_succeeded_persists_result_and_clears_failure_state():
    operation = _operation(attempt_count=1)
    operation.status = "RUNNING"
    operation.error_json = {"code": "RuntimeError", "message": "temporary"}
    finished_at = datetime(2026, 5, 20, 9, 4, tzinfo=timezone.utc)

    mark_operation_succeeded(
        operation=operation,
        response=_response(),
        finished_at=finished_at,
    )

    assert operation.status == "SUCCEEDED"
    assert operation.proposal_id == "pp_async_state"
    assert operation.result_json is not None
    assert operation.result_json["proposal"]["proposal_id"] == "pp_async_state"
    assert operation.error_json is None
    assert operation.lease_expires_at is None
    assert operation.finished_at == finished_at


def test_mark_operation_failed_records_failure_payload():
    operation = _operation(attempt_count=1)
    finished_at = datetime(2026, 5, 20, 9, 5, tzinfo=timezone.utc)

    mark_operation_failed(
        operation=operation,
        code="ProposalLifecycleError",
        message="PROPOSAL_ASYNC_PAYLOAD_INVALID",
        finished_at=finished_at,
    )

    assert operation.status == "FAILED"
    assert operation.result_json is None
    assert operation.error_json == {
        "code": "ProposalLifecycleError",
        "message": "PROPOSAL_ASYNC_PAYLOAD_INVALID",
    }
    assert operation.lease_expires_at is None
    assert operation.finished_at == finished_at


def test_runtime_exception_requeues_until_max_attempts_then_fails():
    finished_at = datetime(2026, 5, 20, 9, 6, tzinfo=timezone.utc)
    requeued = _operation(attempt_count=1, max_attempts=3)

    should_requeue = apply_runtime_exception_outcome(
        operation=requeued,
        exc=TimeoutError(),
        finished_at=finished_at,
    )

    assert should_requeue is True
    assert requeued.status == "PENDING"
    assert requeued.error_json == {"code": "TimeoutError", "message": "TimeoutError"}
    assert requeued.finished_at is None

    failed = _operation(attempt_count=3, max_attempts=3)
    should_requeue = apply_runtime_exception_outcome(
        operation=failed,
        exc=RuntimeError("downstream unavailable"),
        finished_at=finished_at,
    )

    assert should_requeue is False
    assert failed.status == "FAILED"
    assert failed.error_json == {
        "code": "RuntimeError",
        "message": "downstream unavailable",
    }
    assert failed.finished_at == finished_at


def test_build_async_replay_lineage_keeps_operation_identity():
    assert build_async_replay_lineage(_operation()) == {
        "async_operation_id": "pop_async_state",
        "async_operation_type": "CREATE_PROPOSAL",
        "correlation_id": "corr_async_state",
        "idempotency_key": "idem_async_state",
    }


def test_extract_async_result_version_no_reads_successful_result_payload():
    operation = _operation(attempt_count=1)
    operation.result_json = {"version": {"version_no": 2}}

    assert extract_async_result_version_no(operation) == 2


def test_extract_async_result_version_no_rejects_missing_or_malformed_payload():
    operation = _operation(attempt_count=1)
    assert extract_async_result_version_no(operation) is None

    operation.result_json = {"version": None}
    assert extract_async_result_version_no(operation) is None

    operation.result_json = {"version": {"version_no": "2"}}
    assert extract_async_result_version_no(operation) is None
