from datetime import datetime, timezone

from src.core.proposals.create_persistence import persist_created_proposal
from src.core.proposals.models import ProposalVersionRecord
from src.core.proposals.records import build_proposal_create_command_state
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
