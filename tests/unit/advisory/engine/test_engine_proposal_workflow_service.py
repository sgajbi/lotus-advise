from datetime import datetime, timezone

from src.core.proposals.models import (
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
        payload=_create_payload(),
        idempotency_key="idem-missing",
        correlation_id="corr-missing",
    )
    service.execute_create_version_async(
        operation_id="pop_missing",
        proposal_id="pp_missing",
        payload=ProposalVersionRequest(
            created_by="advisor_service",
            simulate_request=_simulate_request(),
        ),
        correlation_id="corr-missing",
    )


def test_service_execute_create_proposal_async_marks_failed_on_lifecycle_error():
    repo = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repo)
    accepted = service.submit_create_proposal_async(
        payload=_create_payload(),
        idempotency_key="idem-async-fail",
        correlation_id="corr-async-fail",
    )

    payload = _create_payload()
    payload.simulate_request.options.enable_proposal_simulation = False
    service.execute_create_proposal_async(
        operation_id=accepted.operation_id,
        payload=payload,
        idempotency_key="idem-async-fail",
        correlation_id="corr-async-fail",
    )

    operation = service.get_async_operation(operation_id=accepted.operation_id)
    assert operation.status == "FAILED"
    assert operation.error is not None
    assert operation.error.code == "ProposalValidationError"


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
