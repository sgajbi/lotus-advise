from datetime import datetime, timezone

from src.core.proposals.async_replay import load_async_operation_replay_referents
from src.core.proposals.models import (
    ProposalAsyncOperationRecord,
    ProposalRecord,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime(2026, 5, 21, 9, 0, tzinfo=timezone.utc)


def _proposal(*, current_version_no: int = 2) -> ProposalRecord:
    return ProposalRecord(
        proposal_id="pp_async_replay",
        portfolio_id="pf_async_replay",
        mandate_id="mandate_async_replay",
        jurisdiction="SG",
        created_by="advisor_async_replay",
        created_at=_now(),
        last_event_at=_now(),
        current_state="DRAFT",
        current_version_no=current_version_no,
        title="Async replay proposal",
    )


def _version(version_no: int) -> ProposalVersionRecord:
    return ProposalVersionRecord(
        proposal_version_id=f"ppv_async_replay_{version_no}",
        proposal_id="pp_async_replay",
        version_no=version_no,
        created_at=_now(),
        request_hash=f"sha256:req-{version_no}",
        artifact_hash=f"sha256:artifact-{version_no}",
        simulation_hash=f"sha256:sim-{version_no}",
        status_at_creation="READY",
        proposal_result_json={"version_no": version_no},
        artifact_json={},
        evidence_bundle_json={},
        gate_decision_json=None,
    )


def _event() -> ProposalWorkflowEventRecord:
    return ProposalWorkflowEventRecord(
        event_id="pwe_async_replay",
        proposal_id="pp_async_replay",
        event_type="CREATED",
        from_state=None,
        to_state="DRAFT",
        actor_id="advisor_async_replay",
        occurred_at=_now(),
        reason_json={},
        related_version_no=1,
    )


def _operation(
    *,
    status: str = "SUCCEEDED",
    proposal_id: str | None = "pp_async_replay",
    result_json: dict | None = None,
) -> ProposalAsyncOperationRecord:
    return ProposalAsyncOperationRecord(
        operation_id="pop_async_replay",
        operation_type="CREATE_PROPOSAL_VERSION",
        status=status,
        correlation_id="corr_async_replay",
        idempotency_key=None,
        proposal_id=proposal_id,
        created_by="advisor_async_replay",
        created_at=_now(),
        payload_json={},
        result_json=result_json,
    )


def test_load_async_operation_replay_referents_uses_success_result_version():
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal())
    repository.create_version(_version(1))
    repository.create_version(_version(2))
    repository.append_event(_event())

    referents = load_async_operation_replay_referents(
        repository=repository,
        operation=_operation(result_json={"version": {"version_no": 1}}),
    )

    assert referents.proposal is not None
    assert referents.proposal.proposal_id == "pp_async_replay"
    assert referents.version is not None
    assert referents.version.version_no == 1
    assert referents.events is not None
    assert [event.event_id for event in referents.events] == ["pwe_async_replay"]


def test_load_async_operation_replay_referents_falls_back_to_current_version():
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal())
    repository.create_version(_version(1))
    repository.create_version(_version(2))

    referents = load_async_operation_replay_referents(
        repository=repository,
        operation=_operation(result_json={"version": {"version_no": 99}}),
    )

    assert referents.version is not None
    assert referents.version.version_no == 2


def test_load_async_operation_replay_referents_without_proposal_scope_is_empty():
    referents = load_async_operation_replay_referents(
        repository=InMemoryProposalRepository(),
        operation=_operation(proposal_id=None),
    )

    assert referents.proposal is None
    assert referents.version is None
    assert referents.events is None


def test_load_async_operation_replay_referents_without_proposal_record_is_empty():
    referents = load_async_operation_replay_referents(
        repository=InMemoryProposalRepository(),
        operation=_operation(result_json={"version": {"version_no": 1}}),
    )

    assert referents.proposal is None
    assert referents.version is None
    assert referents.events is None


def test_load_async_operation_replay_referents_pending_operation_omits_version():
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal())
    repository.create_version(_version(1))

    referents = load_async_operation_replay_referents(
        repository=repository,
        operation=_operation(status="PENDING", result_json=None),
    )

    assert referents.proposal is not None
    assert referents.version is None
    assert referents.events == []
