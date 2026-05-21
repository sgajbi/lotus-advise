from datetime import datetime, timezone

from src.core.proposals.create_persistence import (
    persist_created_proposal,
    persist_created_proposal_version,
)
from src.core.proposals.models import ProposalRecord, ProposalVersionRecord
from src.core.proposals.records import build_proposal_create_command_state
from src.core.proposals.versions import build_new_version_created_event_and_apply_state
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _created_at() -> datetime:
    return datetime(2026, 5, 21, 20, 0, tzinfo=timezone.utc)


def _command_state():
    return build_proposal_create_command_state(
        proposal_id="pp_create_persist",
        portfolio_id="pf_create_persist",
        mandate_id="mandate_create_persist",
        jurisdiction="SG",
        created_by="advisor_create_persist",
        created_at=_created_at(),
        version_no=1,
        title="Create persistence proposal",
        advisor_notes="Initial advisory proposal.",
        lifecycle_origin="DIRECT_CREATE",
        source_workspace_id=None,
        event_id="pwe_create_persist",
        correlation_id="corr_create_persist",
        idempotency_key="idem_create_persist",
        request_hash="sha256:create-persist",
    )


def _version() -> ProposalVersionRecord:
    return ProposalVersionRecord(
        proposal_version_id="ppv_create_persist",
        proposal_id="pp_create_persist",
        version_no=1,
        created_at=_created_at(),
        request_hash="sha256:create-persist",
        artifact_hash="sha256:artifact-create-persist",
        simulation_hash="sha256:simulation-create-persist",
        status_at_creation="READY",
        proposal_result_json={"status": "READY"},
        artifact_json={},
        evidence_bundle_json={},
        gate_decision_json=None,
    )


def _proposal() -> ProposalRecord:
    return ProposalRecord(
        proposal_id="pp_create_persist",
        portfolio_id="pf_create_persist",
        mandate_id="mandate_create_persist",
        jurisdiction="SG",
        created_by="advisor_create_persist",
        created_at=_created_at(),
        last_event_at=_created_at(),
        current_state="EXECUTION_READY",
        current_version_no=1,
        title="Create persistence proposal",
    )


def _next_version() -> ProposalVersionRecord:
    return ProposalVersionRecord(
        proposal_version_id="ppv_create_persist_2",
        proposal_id="pp_create_persist",
        version_no=2,
        created_at=_created_at(),
        request_hash="sha256:create-persist-v2",
        artifact_hash="sha256:artifact-create-persist-v2",
        simulation_hash="sha256:simulation-create-persist-v2",
        status_at_creation="READY",
        proposal_result_json={"status": "READY"},
        artifact_json={},
        evidence_bundle_json={},
        gate_decision_json=None,
    )


def test_persist_created_proposal_stores_initial_referents_and_replay_identity():
    repository = InMemoryProposalRepository()
    command_state = _command_state()
    version = _version()

    persist_created_proposal(
        repository=repository,
        command_state=command_state,
        version=version,
    )

    proposal = repository.get_proposal(proposal_id="pp_create_persist")
    assert proposal is not None
    assert proposal.current_version_no == 1
    assert repository.get_version(proposal_id="pp_create_persist", version_no=1) == version
    assert repository.list_events(proposal_id="pp_create_persist")[0].event_id == (
        "pwe_create_persist"
    )
    idempotency = repository.get_idempotency(idempotency_key="idem_create_persist")
    assert idempotency is not None
    assert idempotency.proposal_id == "pp_create_persist"
    assert idempotency.proposal_version_no == 1


def test_persist_created_proposal_version_stores_version_and_transition_event():
    repository = InMemoryProposalRepository()
    proposal = _proposal()
    repository.create_proposal(proposal)
    version = _next_version()
    event = build_new_version_created_event_and_apply_state(
        event_id="pwe_create_persist_v2",
        proposal=proposal,
        actor_id="advisor_create_persist",
        occurred_at=_created_at(),
        related_version_no=2,
        correlation_id="corr_create_persist_v2",
    )

    persist_created_proposal_version(
        repository=repository,
        proposal=proposal,
        version=version,
        event=event,
    )

    stored_proposal = repository.get_proposal(proposal_id="pp_create_persist")
    assert stored_proposal is not None
    assert stored_proposal.current_version_no == 2
    assert stored_proposal.current_state == "DRAFT"
    assert repository.get_version(proposal_id="pp_create_persist", version_no=2) == version
    events = repository.list_events(proposal_id="pp_create_persist")
    assert events[0].event_id == "pwe_create_persist_v2"
    assert events[0].related_version_no == 2
