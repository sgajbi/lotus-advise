from datetime import datetime, timezone

from src.core.proposals.detail_read_model import load_proposal_detail_read_model
from src.core.proposals.models import ProposalRecord, ProposalVersionRecord
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime(2026, 5, 21, 13, 0, tzinfo=timezone.utc)


def _proposal(*, current_version_no: int = 1) -> ProposalRecord:
    return ProposalRecord(
        proposal_id="pp_detail",
        portfolio_id="pf_detail",
        mandate_id="mandate_detail",
        jurisdiction="SG",
        created_by="advisor_detail",
        created_at=_now(),
        last_event_at=_now(),
        current_state="DRAFT",
        current_version_no=current_version_no,
        title="Detail read model proposal",
    )


def _version(*, version_no: int) -> ProposalVersionRecord:
    return ProposalVersionRecord(
        proposal_version_id=f"ppv_detail_{version_no}",
        proposal_id="pp_detail",
        version_no=version_no,
        created_at=_now(),
        request_hash=f"sha256:req-detail-{version_no}",
        artifact_hash=f"sha256:artifact-detail-{version_no}",
        simulation_hash=f"sha256:sim-detail-{version_no}",
        status_at_creation="READY",
        proposal_result_json={"status": "READY"},
        artifact_json={},
        evidence_bundle_json={},
        gate_decision_json=None,
    )


def test_load_proposal_detail_read_model_returns_proposal_and_current_version():
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal(current_version_no=2))
    repository.create_version(_version(version_no=1))
    repository.create_version(_version(version_no=2))

    read_model = load_proposal_detail_read_model(
        repository=repository,
        proposal_id="pp_detail",
    )

    assert read_model.proposal is not None
    assert read_model.proposal.proposal_id == "pp_detail"
    assert read_model.current_version is not None
    assert read_model.current_version.version_no == 2


def test_load_proposal_detail_read_model_preserves_missing_proposal_boundary():
    read_model = load_proposal_detail_read_model(
        repository=InMemoryProposalRepository(),
        proposal_id="pp_missing",
    )

    assert read_model.proposal is None
    assert read_model.current_version is None


def test_load_proposal_detail_read_model_preserves_missing_current_version_boundary():
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal(current_version_no=1))

    read_model = load_proposal_detail_read_model(
        repository=repository,
        proposal_id="pp_detail",
    )

    assert read_model.proposal is not None
    assert read_model.current_version is None
