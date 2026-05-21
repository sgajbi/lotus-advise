from datetime import datetime, timezone

from src.core.proposals.lineage_read_model import load_proposal_lineage_read_model
from src.core.proposals.models import ProposalRecord, ProposalVersionRecord
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime(2026, 5, 21, 14, 0, tzinfo=timezone.utc)


def _proposal(*, current_version_no: int = 2) -> ProposalRecord:
    return ProposalRecord(
        proposal_id="pp_lineage_read",
        portfolio_id="pf_lineage_read",
        mandate_id="mandate_lineage_read",
        jurisdiction="SG",
        created_by="advisor_lineage_read",
        created_at=_now(),
        last_event_at=_now(),
        current_state="DRAFT",
        current_version_no=current_version_no,
        title="Lineage read model proposal",
    )


def _version(*, version_no: int) -> ProposalVersionRecord:
    return ProposalVersionRecord(
        proposal_version_id=f"ppv_lineage_read_{version_no}",
        proposal_id="pp_lineage_read",
        version_no=version_no,
        created_at=_now(),
        request_hash=f"sha256:req-lineage-read-{version_no}",
        artifact_hash=f"sha256:artifact-lineage-read-{version_no}",
        simulation_hash=f"sha256:sim-lineage-read-{version_no}",
        status_at_creation="READY",
        proposal_result_json={"status": "READY"},
        artifact_json={},
        evidence_bundle_json={},
        gate_decision_json=None,
    )


def test_load_proposal_lineage_read_model_returns_proposal_and_versions_by_number():
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal(current_version_no=2))
    repository.create_version(_version(version_no=1))
    repository.create_version(_version(version_no=2))

    read_model = load_proposal_lineage_read_model(
        repository=repository,
        proposal_id="pp_lineage_read",
    )

    assert read_model.proposal is not None
    assert read_model.proposal.proposal_id == "pp_lineage_read"
    assert sorted(read_model.versions_by_number) == [1, 2]
    assert read_model.versions_by_number[2] is not None
    assert read_model.versions_by_number[2].proposal_version_id == "ppv_lineage_read_2"


def test_load_proposal_lineage_read_model_preserves_missing_proposal_boundary():
    read_model = load_proposal_lineage_read_model(
        repository=InMemoryProposalRepository(),
        proposal_id="pp_missing",
    )

    assert read_model.proposal is None
    assert read_model.versions_by_number == {}


def test_load_proposal_lineage_read_model_preserves_missing_version_gap_boundary():
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal(current_version_no=2))
    repository.create_version(_version(version_no=1))

    read_model = load_proposal_lineage_read_model(
        repository=repository,
        proposal_id="pp_lineage_read",
    )

    assert read_model.proposal is not None
    assert sorted(read_model.versions_by_number) == [1]
    assert 2 not in read_model.versions_by_number
