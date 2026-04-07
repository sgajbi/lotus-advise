from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

from src.core.advisory_engine import run_proposal_simulation
from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalApprovalRequest,
    ProposalCreateRequest,
    ProposalIdempotencyRecord,
    ProposalRecord,
    ProposalStateTransitionRequest,
    ProposalVersionRecord,
    ProposalVersionRequest,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.service import (
    ProposalIdempotencyConflictError,
    ProposalLifecycleError,
    ProposalNotFoundError,
    ProposalStateConflictError,
    ProposalTransitionError,
    ProposalValidationError,
    ProposalWorkflowService,
)
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _simulate_request(portfolio_id: str = "pf_service_1") -> dict:
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


def _create_payload() -> ProposalCreateRequest:
    return ProposalCreateRequest(
        created_by="advisor_service",
        simulate_request=_simulate_request(),
        metadata={"title": "Service test"},
    )


@pytest.fixture(autouse=True)
def reset_upstream_authority_overrides(monkeypatch):
    monkeypatch.delenv("LOTUS_CORE_BASE_URL", raising=False)
    monkeypatch.delenv("LOTUS_RISK_BASE_URL", raising=False)
    monkeypatch.delenv("LOTUS_ADVISE_ALLOW_LOCAL_SIMULATION_FALLBACK", raising=False)

    def _simulate_with_lotus_core(**kwargs):
        request = kwargs["request"]
        return run_proposal_simulation(
            portfolio=request.portfolio_snapshot,
            market_data=request.market_data_snapshot,
            shelf=request.shelf_entries,
            options=request.options,
            proposed_cash_flows=request.proposed_cash_flows,
            proposed_trades=request.proposed_trades,
            reference_model=request.reference_model,
            request_hash=kwargs["request_hash"],
            idempotency_key=kwargs["idempotency_key"],
            correlation_id=kwargs["correlation_id"],
            simulation_contract_version="advisory-simulation.v1",
        )

    monkeypatch.setattr(
        "src.core.advisory.orchestration.simulate_with_lotus_core",
        _simulate_with_lotus_core,
    )


def test_service_version_payload_is_immutable_from_caller_mutation():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())

    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="service-idem-1",
        correlation_id="corr-service-1",
    )
    proposal_id = created.proposal.proposal_id

    version_one = service.get_version(proposal_id=proposal_id, version_no=1, include_evidence=True)
    version_one.evidence_bundle["hashes"]["artifact_hash"] = "tampered"

    version_again = service.get_version(
        proposal_id=proposal_id, version_no=1, include_evidence=True
    )
    assert version_again.evidence_bundle["hashes"]["artifact_hash"].startswith("sha256:")


def test_service_create_proposal_uses_upstream_simulation_authority_when_available(
    monkeypatch,
):
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())

    def _simulate_with_lotus_core(**kwargs):
        request = kwargs["request"]
        return run_proposal_simulation(
            portfolio=request.portfolio_snapshot,
            market_data=request.market_data_snapshot,
            shelf=request.shelf_entries,
            options=request.options,
            proposed_cash_flows=request.proposed_cash_flows,
            proposed_trades=request.proposed_trades,
            reference_model=request.reference_model,
            request_hash=kwargs["request_hash"],
            idempotency_key=kwargs["idempotency_key"],
            correlation_id=kwargs["correlation_id"],
        )

    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setattr(
        "src.core.advisory.orchestration.simulate_with_lotus_core",
        _simulate_with_lotus_core,
    )

    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="service-idem-upstream",
        correlation_id="corr-service-upstream",
    )

    authority = created.version.proposal_result.explanation["authority_resolution"]
    assert authority["simulation_authority"] == "lotus_core"
    assert authority["risk_authority"] == "lotus_advise_local"


def test_service_request_hash_is_stable_between_legacy_and_stateless_create_contracts():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())
    legacy_payload = ProposalCreateRequest(
        created_by="advisor_service",
        simulate_request=_simulate_request(),
        metadata={"title": "Service test"},
    )
    stateless_payload = ProposalCreateRequest(
        created_by="advisor_service",
        input_mode="stateless",
        stateless_input={"simulate_request": _simulate_request()},
        metadata={"title": "Service test"},
    )

    legacy = service.create_proposal(
        payload=legacy_payload,
        idempotency_key="service-idem-legacy-hash",
        correlation_id="corr-service-legacy-hash",
    )
    stateless = service.create_proposal(
        payload=stateless_payload,
        idempotency_key="service-idem-stateless-hash",
        correlation_id="corr-service-stateless-hash",
    )

    assert legacy.version.request_hash == stateless.version.request_hash
    assert legacy.version.simulation_hash == stateless.version.simulation_hash


def test_service_rejects_version_with_portfolio_context_mismatch():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())

    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="service-idem-2",
        correlation_id="corr-service-2",
    )
    proposal_id = created.proposal.proposal_id

    version_payload = ProposalVersionRequest(
        created_by="advisor_service",
        simulate_request=_simulate_request(portfolio_id="pf_other"),
    )

    try:
        service.create_version(
            proposal_id=proposal_id,
            payload=version_payload,
            correlation_id="corr-version-1",
        )
    except ProposalValidationError as exc:
        assert str(exc) == "PORTFOLIO_CONTEXT_MISMATCH"
    else:
        raise AssertionError("Expected PORTFOLIO_CONTEXT_MISMATCH")


def test_service_rejects_version_when_expected_current_version_mismatches():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())

    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="service-idem-version-conflict",
        correlation_id="corr-service-version-conflict",
    )
    proposal_id = created.proposal.proposal_id

    version_payload = ProposalVersionRequest(
        created_by="advisor_service",
        expected_current_version_no=2,
        simulate_request=_simulate_request(),
    )

    try:
        service.create_version(
            proposal_id=proposal_id,
            payload=version_payload,
            correlation_id="corr-version-conflict",
        )
    except ProposalStateConflictError as exc:
        assert str(exc) == "VERSION_CONFLICT: expected_current_version_no mismatch"
    else:
        raise AssertionError("Expected VERSION_CONFLICT: expected_current_version_no mismatch")


def test_service_rejects_invalid_transition_for_current_state():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())

    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="service-idem-3",
        correlation_id="corr-service-3",
    )

    try:
        service.transition_state(
            proposal_id=created.proposal.proposal_id,
            payload=ProposalStateTransitionRequest(
                event_type="RISK_APPROVED",
                actor_id="risk_1",
                expected_state="DRAFT",
                reason={"comment": "invalid"},
            ),
        )
    except ProposalTransitionError as exc:
        assert str(exc) == "INVALID_TRANSITION"
    else:
        raise AssertionError("Expected INVALID_TRANSITION")


def test_service_allows_cancel_from_non_terminal_state():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())

    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="service-idem-4",
        correlation_id="corr-service-4",
    )
    result = service.transition_state(
        proposal_id=created.proposal.proposal_id,
        payload=ProposalStateTransitionRequest(
            event_type="CANCELLED",
            actor_id="advisor_service",
            expected_state="DRAFT",
            reason={"comment": "client withdrew"},
        ),
    )
    assert result.current_state == "CANCELLED"


def test_service_rejects_new_version_for_terminal_state():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())

    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="service-idem-5",
        correlation_id="corr-service-5",
    )
    service.transition_state(
        proposal_id=created.proposal.proposal_id,
        payload=ProposalStateTransitionRequest(
            event_type="CANCELLED",
            actor_id="advisor_service",
            expected_state="DRAFT",
            reason={},
        ),
    )

    try:
        service.create_version(
            proposal_id=created.proposal.proposal_id,
            payload=ProposalVersionRequest(
                created_by="advisor_service",
                simulate_request=_simulate_request(),
            ),
            correlation_id="corr-service-5-version",
        )
    except ProposalValidationError as exc:
        assert str(exc) == "PROPOSAL_TERMINAL_STATE: cannot create version"
    else:
        raise AssertionError("Expected PROPOSAL_TERMINAL_STATE")


def test_service_records_rejected_client_consent_path():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())
    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="service-idem-6",
        correlation_id="corr-service-6",
    )

    service.transition_state(
        proposal_id=created.proposal.proposal_id,
        payload=ProposalStateTransitionRequest(
            event_type="SUBMITTED_FOR_RISK_REVIEW",
            actor_id="advisor_service",
            expected_state="DRAFT",
            reason={},
        ),
    )
    service.record_approval(
        proposal_id=created.proposal.proposal_id,
        payload=ProposalApprovalRequest(
            approval_type="RISK",
            approved=True,
            actor_id="risk_officer",
            expected_state="RISK_REVIEW",
            details={},
        ),
    )
    rejected = service.record_approval(
        proposal_id=created.proposal.proposal_id,
        payload=ProposalApprovalRequest(
            approval_type="CLIENT_CONSENT",
            approved=False,
            actor_id="client",
            expected_state="AWAITING_CLIENT_CONSENT",
            details={"reason": "declined"},
        ),
    )

    assert rejected.current_state == "REJECTED"
    assert rejected.latest_workflow_event.event_type == "REJECTED"


def test_service_get_proposal_and_version_raise_not_found_paths():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())

    try:
        service.get_proposal(proposal_id="pp_missing", include_evidence=True)
    except ProposalNotFoundError as exc:
        assert str(exc) == "PROPOSAL_NOT_FOUND"
    else:
        raise AssertionError("Expected PROPOSAL_NOT_FOUND")

    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    now = datetime.now(timezone.utc)
    repo.create_proposal(
        ProposalRecord(
            proposal_id="pp_only_proposal",
            portfolio_id="pf_service_1",
            mandate_id=None,
            jurisdiction=None,
            created_by="advisor",
            created_at=now,
            last_event_at=now,
            current_state="DRAFT",
            current_version_no=1,
            title=None,
            advisor_notes=None,
        )
    )
    try:
        service.get_proposal(proposal_id="pp_only_proposal", include_evidence=True)
    except ProposalNotFoundError as exc:
        assert str(exc) == "PROPOSAL_VERSION_NOT_FOUND"
    else:
        raise AssertionError("Expected PROPOSAL_VERSION_NOT_FOUND")


def test_service_missing_version_paths_and_helper_branches():
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)

    try:
        service.get_version(proposal_id="pp_missing", version_no=1, include_evidence=True)
    except ProposalNotFoundError as exc:
        assert str(exc) == "PROPOSAL_VERSION_NOT_FOUND"
    else:
        raise AssertionError("Expected PROPOSAL_VERSION_NOT_FOUND")

    try:
        service.create_version(
            proposal_id="pp_missing",
            payload=ProposalVersionRequest(
                created_by="advisor",
                simulate_request=_simulate_request(),
            ),
            correlation_id=None,
        )
    except ProposalNotFoundError as exc:
        assert str(exc) == "PROPOSAL_NOT_FOUND"
    else:
        raise AssertionError("Expected PROPOSAL_NOT_FOUND")

    try:
        service.transition_state(
            proposal_id="pp_missing",
            payload=ProposalStateTransitionRequest(
                event_type="SUBMITTED_FOR_RISK_REVIEW",
                actor_id="advisor",
                expected_state="DRAFT",
                reason={},
            ),
        )
    except ProposalNotFoundError as exc:
        assert str(exc) == "PROPOSAL_NOT_FOUND"
    else:
        raise AssertionError("Expected PROPOSAL_NOT_FOUND")

    try:
        service.record_approval(
            proposal_id="pp_missing",
            payload=ProposalApprovalRequest(
                approval_type="RISK",
                approved=True,
                actor_id="risk",
                expected_state="RISK_REVIEW",
                details={},
            ),
        )
    except ProposalNotFoundError as exc:
        assert str(exc) == "PROPOSAL_NOT_FOUND"
    else:
        raise AssertionError("Expected PROPOSAL_NOT_FOUND")

    assert service._to_approval(None) is None

    repo.save_idempotency(
        ProposalIdempotencyRecord(
            idempotency_key="idem-bad-ref",
            request_hash="sha256:x",
            proposal_id="pp_missing",
            proposal_version_no=1,
            created_at=datetime.now(timezone.utc),
        )
    )
    try:
        service._read_create_response(proposal_id="pp_missing", version_no=1)
    except ProposalNotFoundError as exc:
        assert str(exc) == "PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND"
    else:
        raise AssertionError("Expected PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND")


def test_service_rejects_simulation_flag_and_invalid_approval_type():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())
    payload = _create_payload()
    payload.simulate_request.options.enable_proposal_simulation = False

    try:
        service.create_proposal(
            payload=payload,
            idempotency_key="service-idem-disabled",
            correlation_id=None,
        )
    except ProposalValidationError as exc:
        assert "PROPOSAL_SIMULATION_DISABLED" in str(exc)
    else:
        raise AssertionError("Expected PROPOSAL_SIMULATION_DISABLED")

    try:
        service._resolve_approval_transition(
            current_state="DRAFT",
            approval_type="UNKNOWN",
            approved=True,
        )
    except ProposalTransitionError as exc:
        assert str(exc) == "INVALID_APPROVAL_TYPE"
    else:
        raise AssertionError("Expected INVALID_APPROVAL_TYPE")


def test_service_invalid_approval_state_variants():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())
    for approval_type, expected_state in [
        ("RISK", "COMPLIANCE_REVIEW"),
        ("COMPLIANCE", "RISK_REVIEW"),
        ("CLIENT_CONSENT", "DRAFT"),
    ]:
        try:
            service._resolve_approval_transition(
                current_state=expected_state,
                approval_type=approval_type,
                approved=True,
            )
        except ProposalTransitionError as exc:
            assert str(exc) == "INVALID_APPROVAL_STATE"
        else:
            raise AssertionError("Expected INVALID_APPROVAL_STATE")


def test_service_execute_async_returns_when_operation_missing():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())
    service.execute_create_proposal_async(
        operation_id="pop_missing",
    )
    service.execute_create_version_async(
        operation_id="pop_missing",
    )


def test_service_execute_create_proposal_async_marks_failed_on_lifecycle_error():
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    accepted = service.submit_create_proposal_async(
        payload=_create_payload(),
        idempotency_key="idem-async-fail",
        correlation_id="corr-async-fail",
    )

    stored_operation = repo.get_operation(operation_id=accepted.operation_id)
    assert stored_operation is not None
    stored_operation.payload_json["payload"]["simulate_request"]["options"][
        "enable_proposal_simulation"
    ] = False
    repo.update_operation(stored_operation)

    service.execute_create_proposal_async(operation_id=accepted.operation_id)

    operation = service.get_async_operation(operation_id=accepted.operation_id)
    assert operation.status == "FAILED"
    assert operation.error is not None
    assert operation.error.code == "ProposalValidationError"
    assert operation.attempt_count == 1
    assert operation.max_attempts == 3
    assert operation.lease_expires_at is None


def test_service_execute_create_version_async_marks_failed_on_lifecycle_error():
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    accepted = service.submit_create_version_async(
        proposal_id="pp_missing_for_async_version",
        payload=ProposalVersionRequest(
            created_by="advisor_service",
            simulate_request=_simulate_request(),
        ),
        correlation_id="corr-async-version-fail",
    )

    service.execute_create_version_async(
        operation_id=accepted.operation_id,
        proposal_id="pp_missing_for_async_version",
        payload=ProposalVersionRequest(
            created_by="advisor_service",
            simulate_request=_simulate_request(),
        ),
        correlation_id="corr-async-version-fail",
    )

    operation = service.get_async_operation(operation_id=accepted.operation_id)
    assert operation.status == "FAILED"
    assert operation.error is not None
    assert operation.error.code == "ProposalNotFoundError"
    assert operation.error.message == "PROPOSAL_NOT_FOUND"
    assert operation.attempt_count == 1
    assert operation.max_attempts == 3
    assert operation.lease_expires_at is None


def test_service_accept_async_version_submission_replays_duplicate_correlation() -> None:
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="idem-async-version-replay-base",
        correlation_id="corr-async-version-replay-base",
    )
    payload = ProposalVersionRequest(
        created_by="advisor_service",
        simulate_request=_simulate_request(),
    )

    first, first_is_new = service.accept_create_version_async_submission(
        proposal_id=created.proposal.proposal_id,
        payload=payload,
        correlation_id="corr-async-version-replay",
    )
    replayed, replayed_is_new = service.accept_create_version_async_submission(
        proposal_id=created.proposal.proposal_id,
        payload=payload,
        correlation_id="corr-async-version-replay",
    )

    assert first_is_new is True
    assert replayed_is_new is False
    assert replayed.operation_id == first.operation_id
    assert replayed.correlation_id == first.correlation_id


def test_service_accept_async_version_submission_rejects_correlation_mismatch() -> None:
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="idem-async-version-conflict-base",
        correlation_id="corr-async-version-conflict-base",
    )
    payload = ProposalVersionRequest(
        created_by="advisor_service",
        simulate_request=_simulate_request(),
    )
    conflicting_payload = ProposalVersionRequest(
        created_by="advisor_service_conflict",
        simulate_request=_simulate_request(),
    )

    accepted, accepted_is_new = service.accept_create_version_async_submission(
        proposal_id=created.proposal.proposal_id,
        payload=payload,
        correlation_id="corr-async-version-conflict",
    )

    with pytest.raises(ProposalIdempotencyConflictError) as exc_info:
        service.accept_create_version_async_submission(
            proposal_id=created.proposal.proposal_id,
            payload=conflicting_payload,
            correlation_id="corr-async-version-conflict",
        )

    assert accepted_is_new is True
    assert accepted.operation_id.startswith("pop_")
    assert str(exc_info.value) == "CORRELATION_ID_CONFLICT: async version submission mismatch"


def test_service_submit_async_create_persists_restart_safe_payload():
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    payload = _create_payload()

    accepted = service.submit_create_proposal_async(
        payload=payload,
        idempotency_key="idem-async-persisted-payload",
        correlation_id="corr-async-persisted-payload",
    )

    stored = repo.get_operation(operation_id=accepted.operation_id)
    assert stored is not None
    assert stored.payload_json["idempotency_key"] == "idem-async-persisted-payload"
    assert stored.payload_json["payload"]["created_by"] == payload.created_by
    assert stored.attempt_count == 0
    assert stored.max_attempts == 3
    assert accepted.attempt_count == 0
    assert accepted.max_attempts == 3


def test_service_accept_async_create_submission_marks_replayed_duplicates() -> None:
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    payload = _create_payload()

    first, first_is_new = service.accept_create_proposal_async_submission(
        payload=payload,
        idempotency_key="idem-async-replayed-create",
        correlation_id="corr-async-replayed-create-1",
    )
    duplicate, duplicate_is_new = service.accept_create_proposal_async_submission(
        payload=payload,
        idempotency_key="idem-async-replayed-create",
        correlation_id="corr-async-replayed-create-2",
    )

    assert first_is_new is True
    assert duplicate_is_new is False
    assert duplicate.operation_id == first.operation_id
    assert duplicate.correlation_id == first.correlation_id
    stats = service.get_async_create_submission_stats_for_tests()
    assert stats.accepted_new == 1
    assert stats.accepted_replayed == 1
    assert stats.conflicts == 0


def test_service_accept_async_create_submission_is_concurrency_safe() -> None:
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    payload = _create_payload()

    def _submit() -> tuple[str, bool]:
        accepted, is_new = service.accept_create_proposal_async_submission(
            payload=payload,
            idempotency_key="idem-async-concurrent-create",
            correlation_id=None,
        )
        return accepted.operation_id, is_new

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: _submit(), range(24)))

    operation_ids = {operation_id for operation_id, _ in results}
    new_flags = [is_new for _, is_new in results]
    assert len(operation_ids) == 1
    assert sum(1 for value in new_flags if value) == 1
    stats = service.get_async_create_submission_stats_for_tests()
    assert stats.accepted_new == 1
    assert stats.accepted_replayed == 23
    assert stats.conflicts == 0


def test_service_accept_async_create_submission_tracks_conflicts() -> None:
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    payload = _create_payload()

    service.accept_create_proposal_async_submission(
        payload=payload,
        idempotency_key="idem-async-conflict-stats",
        correlation_id="corr-async-conflict-stats-1",
    )

    conflicting_payload = _create_payload()
    conflicting_payload.metadata.title = "Conflicting async stats payload"

    with pytest.raises(ProposalIdempotencyConflictError):
        service.accept_create_proposal_async_submission(
            payload=conflicting_payload,
            idempotency_key="idem-async-conflict-stats",
            correlation_id="corr-async-conflict-stats-2",
        )

    stats = service.get_async_create_submission_stats_for_tests()
    assert stats.accepted_new == 1
    assert stats.accepted_replayed == 0
    assert stats.conflicts == 1


def test_service_execute_create_proposal_async_retries_runtime_failure(monkeypatch):
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    accepted = service.submit_create_proposal_async(
        payload=_create_payload(),
        idempotency_key="idem-async-runtime-retry",
        correlation_id="corr-async-runtime-retry",
    )

    original_create_proposal = service.create_proposal
    attempts = {"count": 0}

    def flaky_create_proposal(**kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient runtime outage")
        return original_create_proposal(**kwargs)

    monkeypatch.setattr(service, "create_proposal", flaky_create_proposal)

    service.execute_create_proposal_async(operation_id=accepted.operation_id)

    operation = service.get_async_operation(operation_id=accepted.operation_id)
    assert operation.status == "SUCCEEDED"
    assert operation.result is not None
    assert operation.error is None
    assert operation.attempt_count == 2
    assert attempts["count"] == 2


def test_service_recover_async_operations_replays_pending_create_from_persisted_payload():
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    accepted = service.submit_create_proposal_async(
        payload=_create_payload(),
        idempotency_key="idem-async-recover-pending",
        correlation_id="corr-async-recover-pending",
    )

    recovered = service.recover_async_operations()

    operation = service.get_async_operation(operation_id=accepted.operation_id)
    assert recovered == 1
    assert operation.status == "SUCCEEDED"
    assert operation.result is not None
    assert operation.result.proposal.proposal_id


def test_service_recover_async_operations_replays_expired_running_version_operation():
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="idem-async-expired-running-base",
        correlation_id="corr-async-expired-running-base",
    )
    accepted = service.submit_create_version_async(
        proposal_id=created.proposal.proposal_id,
        payload=ProposalVersionRequest(
            created_by="advisor_service",
            simulate_request=_simulate_request(),
        ),
        correlation_id="corr-async-expired-running-version",
    )
    operation = repo.get_operation(operation_id=accepted.operation_id)
    assert operation is not None
    operation.status = "RUNNING"
    operation.attempt_count = 1
    operation.started_at = datetime.now(timezone.utc)
    operation.lease_expires_at = datetime.now(timezone.utc)
    repo.update_operation(operation)

    recovered = service.recover_async_operations()

    status = service.get_async_operation(operation_id=accepted.operation_id)
    assert recovered == 1
    assert status.status == "SUCCEEDED"
    assert status.attempt_count == 2
    assert status.result is not None


def test_service_expected_state_can_be_optional_when_disabled():
    service = ProposalWorkflowService(
        repository=InMemoryProposalRepository(),
        require_expected_state=False,
    )
    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="service-idem-optional-state",
        correlation_id="corr-service-optional-state",
    )
    transitioned = service.transition_state(
        proposal_id=created.proposal.proposal_id,
        payload=ProposalStateTransitionRequest(
            event_type="SUBMITTED_FOR_RISK_REVIEW",
            actor_id="advisor_service",
            expected_state=None,
            reason={},
        ),
    )
    assert transitioned.current_state == "RISK_REVIEW"

    strict_service = ProposalWorkflowService(
        repository=InMemoryProposalRepository(),
        require_expected_state=True,
    )
    strict_created = strict_service.create_proposal(
        payload=_create_payload(),
        idempotency_key="service-idem-required-state",
        correlation_id="corr-service-required-state",
    )
    try:
        strict_service.transition_state(
            proposal_id=strict_created.proposal.proposal_id,
            payload=ProposalStateTransitionRequest(
                event_type="SUBMITTED_FOR_RISK_REVIEW",
                actor_id="advisor_service",
                expected_state=None,
                reason={},
            ),
        )
    except ProposalStateConflictError as exc:
        assert "expected_state is required" in str(exc)
    else:
        raise AssertionError("Expected ProposalStateConflictError")


def test_service_lineage_skips_missing_version_rows():
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    now = datetime.now(timezone.utc)
    repo.create_proposal(
        ProposalRecord(
            proposal_id="pp_lineage_gap",
            portfolio_id="pf_lineage_gap",
            mandate_id=None,
            jurisdiction=None,
            created_by="advisor",
            created_at=now,
            last_event_at=now,
            current_state="DRAFT",
            current_version_no=2,
            title="lineage gap",
            advisor_notes=None,
        )
    )
    repo.create_version(
        ProposalVersionRecord(
            proposal_version_id="ppv_lineage_gap_1",
            proposal_id="pp_lineage_gap",
            version_no=1,
            created_at=now,
            request_hash="sha256:req-lineage-gap-1",
            artifact_hash="sha256:artifact-lineage-gap-1",
            simulation_hash="sha256:sim-lineage-gap-1",
            status_at_creation="READY",
            proposal_result_json={"proposal_run_id": "pr_lineage_gap_1", "status": "READY"},
            artifact_json={"artifact_id": "pa_lineage_gap_1"},
            evidence_bundle_json={},
            gate_decision_json=None,
        )
    )
    repo.append_event(
        ProposalWorkflowEventRecord(
            event_id="pwe_lineage_gap_created",
            proposal_id="pp_lineage_gap",
            event_type="CREATED",
            from_state=None,
            to_state="DRAFT",
            actor_id="advisor",
            occurred_at=now,
            reason_json={},
            related_version_no=1,
        )
    )

    lineage = service.get_lineage(proposal_id="pp_lineage_gap")
    assert lineage.proposal.proposal_id == "pp_lineage_gap"
    assert lineage.version_count == 1
    assert lineage.latest_version_no == 1
    assert lineage.lineage_complete is False
    assert lineage.missing_version_numbers == [2]
    assert [version.version_no for version in lineage.versions] == [1]


def test_transition_idempotency_replay_and_conflict():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())
    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="service-idem-transition",
        correlation_id="corr-transition",
    )
    proposal_id = created.proposal.proposal_id
    payload = ProposalStateTransitionRequest(
        event_type="SUBMITTED_FOR_RISK_REVIEW",
        actor_id="advisor_service",
        expected_state="DRAFT",
        reason={"comment": "first submit"},
    )
    first = service.transition_state(
        proposal_id=proposal_id,
        payload=payload,
        idempotency_key="idem-transition-1",
    )
    replay = service.transition_state(
        proposal_id=proposal_id,
        payload=payload,
        idempotency_key="idem-transition-1",
    )
    assert replay.latest_workflow_event.event_id == first.latest_workflow_event.event_id
    assert replay.current_state == "RISK_REVIEW"

    try:
        service.transition_state(
            proposal_id=proposal_id,
            payload=ProposalStateTransitionRequest(
                event_type="SUBMITTED_FOR_COMPLIANCE_REVIEW",
                actor_id="advisor_service",
                expected_state="RISK_REVIEW",
                reason={"comment": "different request"},
            ),
            idempotency_key="idem-transition-1",
        )
    except ProposalIdempotencyConflictError as exc:
        assert "IDEMPOTENCY_KEY_CONFLICT" in str(exc)
    else:
        raise AssertionError("Expected ProposalIdempotencyConflictError")


def test_approval_idempotency_replay_and_conflict():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())
    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="service-idem-approval",
        correlation_id="corr-approval",
    )
    proposal_id = created.proposal.proposal_id
    service.transition_state(
        proposal_id=proposal_id,
        payload=ProposalStateTransitionRequest(
            event_type="SUBMITTED_FOR_RISK_REVIEW",
            actor_id="advisor_service",
            expected_state="DRAFT",
            reason={},
        ),
    )
    approval_payload = ProposalApprovalRequest(
        approval_type="RISK",
        approved=True,
        actor_id="risk_officer",
        expected_state="RISK_REVIEW",
        details={"comment": "approved"},
    )
    first = service.record_approval(
        proposal_id=proposal_id,
        payload=approval_payload,
        idempotency_key="idem-approval-1",
    )
    replay = service.record_approval(
        proposal_id=proposal_id,
        payload=approval_payload,
        idempotency_key="idem-approval-1",
    )
    assert replay.latest_workflow_event.event_id == first.latest_workflow_event.event_id
    assert replay.approval is not None
    assert first.approval is not None
    assert replay.approval.approval_id == first.approval.approval_id

    try:
        service.record_approval(
            proposal_id=proposal_id,
            payload=ProposalApprovalRequest(
                approval_type="RISK",
                approved=False,
                actor_id="risk_officer",
                expected_state="RISK_REVIEW",
                details={"comment": "different decision"},
            ),
            idempotency_key="idem-approval-1",
        )
    except ProposalIdempotencyConflictError as exc:
        assert "IDEMPOTENCY_KEY_CONFLICT" in str(exc)
    else:
        raise AssertionError("Expected ProposalIdempotencyConflictError")


def test_approval_replay_requires_matching_event_referent():
    now = datetime.now(timezone.utc)
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="idem-approval-referent",
        correlation_id="corr-approval-referent",
    )
    proposal_id = created.proposal.proposal_id
    service.transition_state(
        proposal_id=proposal_id,
        payload=ProposalStateTransitionRequest(
            event_type="SUBMITTED_FOR_RISK_REVIEW",
            actor_id="advisor_service",
            expected_state="DRAFT",
            reason={},
        ),
    )

    approval_payload = ProposalApprovalRequest(
        approval_type="RISK",
        approved=True,
        actor_id="risk_officer",
        expected_state="RISK_REVIEW",
        details={},
    )
    request_hash = hash_canonical_payload(approval_payload.model_dump(mode="json"))

    repo.create_approval(
        ProposalApprovalRecordData(
            approval_id="pap_orphan",
            proposal_id=proposal_id,
            approval_type="RISK",
            approved=True,
            actor_id="risk_officer",
            occurred_at=now,
            details_json={
                "idempotency_key": "idem-approval-orphan",
                "idempotency_request_hash": request_hash,
            },
            related_version_no=1,
        )
    )

    try:
        service.record_approval(
            proposal_id=proposal_id,
            payload=approval_payload,
            idempotency_key="idem-approval-orphan",
        )
    except ProposalLifecycleError as exc:
        assert str(exc) == "PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND"
    else:
        raise AssertionError("Expected PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND")


def test_approval_replay_skips_unrelated_idempotency_records():
    now = datetime.now(timezone.utc)
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="idem-approval-skip",
        correlation_id="corr-approval-skip",
    )
    proposal_id = created.proposal.proposal_id
    service.transition_state(
        proposal_id=proposal_id,
        payload=ProposalStateTransitionRequest(
            event_type="SUBMITTED_FOR_RISK_REVIEW",
            actor_id="advisor_service",
            expected_state="DRAFT",
            reason={},
        ),
    )

    payload = ProposalApprovalRequest(
        approval_type="RISK",
        approved=True,
        actor_id="risk_officer",
        expected_state="RISK_REVIEW",
        details={},
    )
    first = service.record_approval(
        proposal_id=proposal_id,
        payload=payload,
        idempotency_key="idem-target",
    )
    repo.create_approval(
        ProposalApprovalRecordData(
            approval_id="pap_unrelated",
            proposal_id=proposal_id,
            approval_type="CLIENT_CONSENT",
            approved=False,
            actor_id="client_1",
            occurred_at=now,
            details_json={
                "idempotency_key": "idem-unrelated",
                "idempotency_request_hash": "sha256:unrelated",
            },
            related_version_no=1,
        )
    )

    replay = service.record_approval(
        proposal_id=proposal_id,
        payload=payload,
        idempotency_key="idem-target",
    )
    assert replay.approval is not None
    assert first.approval is not None
    assert replay.approval.approval_id == first.approval.approval_id


def test_service_create_proposal_persists_direct_create_origin_by_default():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())

    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="service-origin-direct",
        correlation_id="corr-service-origin-direct",
    )

    assert created.proposal.lifecycle_origin == "DIRECT_CREATE"
    assert created.proposal.source_workspace_id is None


def test_service_create_proposal_requires_workspace_reference_for_workspace_handoff_origin():
    service = ProposalWorkflowService(repository=InMemoryProposalRepository())

    try:
        service.create_proposal(
            payload=_create_payload(),
            idempotency_key="service-origin-workspace-missing",
            correlation_id="corr-service-origin-workspace-missing",
            lifecycle_origin="WORKSPACE_HANDOFF",
            source_workspace_id=None,
        )
    except ProposalValidationError as exc:
        assert str(exc) == "WORKSPACE_HANDOFF_SOURCE_WORKSPACE_ID_REQUIRED"
    else:
        raise AssertionError("Expected WORKSPACE_HANDOFF_SOURCE_WORKSPACE_ID_REQUIRED")
