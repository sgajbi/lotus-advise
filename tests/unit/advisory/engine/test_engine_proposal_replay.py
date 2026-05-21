from datetime import datetime, timezone

from src.core.proposals.models import (
    ProposalRecord,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.proposal_replay import load_proposal_version_replay_referents
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc)


def _proposal() -> ProposalRecord:
    return ProposalRecord(
        proposal_id="pp_replay",
        portfolio_id="pf_replay",
        mandate_id="mandate_replay",
        jurisdiction="SG",
        created_by="advisor_replay",
        created_at=_now(),
        last_event_at=_now(),
        current_state="DRAFT",
        current_version_no=1,
        title="Replay proposal",
    )


def _version() -> ProposalVersionRecord:
    return ProposalVersionRecord(
        proposal_version_id="ppv_replay_1",
        proposal_id="pp_replay",
        version_no=1,
        created_at=_now(),
        request_hash="sha256:req-replay",
        artifact_hash="sha256:artifact-replay",
        simulation_hash="sha256:sim-replay",
        status_at_creation="READY",
        proposal_result_json={"status": "READY"},
        artifact_json={},
        evidence_bundle_json={},
        gate_decision_json=None,
    )


def _event(event_id: str, related_version_no: int | None = 1) -> ProposalWorkflowEventRecord:
    return ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id="pp_replay",
        event_type="CREATED",
        from_state=None,
        to_state="DRAFT",
        actor_id="advisor_replay",
        occurred_at=_now(),
        reason_json={},
        related_version_no=related_version_no,
    )


def test_load_proposal_version_replay_referents_returns_complete_replay_context():
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal())
    repository.create_version(_version())
    repository.append_event(_event("pwe_replay_1"))
    repository.append_event(_event("pwe_replay_2", related_version_no=None))

    referents = load_proposal_version_replay_referents(
        repository=repository,
        proposal_id="pp_replay",
        version_no=1,
    )

    assert referents.proposal is not None
    assert referents.proposal.proposal_id == "pp_replay"
    assert referents.version is not None
    assert referents.version.proposal_version_id == "ppv_replay_1"
    assert [event.event_id for event in referents.events] == ["pwe_replay_1", "pwe_replay_2"]


def test_load_proposal_version_replay_referents_preserves_missing_proposal_boundary():
    referents = load_proposal_version_replay_referents(
        repository=InMemoryProposalRepository(),
        proposal_id="pp_missing",
        version_no=1,
    )

    assert referents.proposal is None
    assert referents.version is None
    assert referents.events == []


def test_load_proposal_version_replay_referents_preserves_missing_version_boundary():
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal())

    referents = load_proposal_version_replay_referents(
        repository=repository,
        proposal_id="pp_replay",
        version_no=99,
    )

    assert referents.proposal is not None
    assert referents.version is None
    assert referents.events == []
