from datetime import datetime, timezone

from src.core.proposals.models import ProposalRecord, ProposalVersionRecord
from src.core.proposals.version_read_model import load_proposal_version_read_model
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime(2026, 5, 21, 15, 0, tzinfo=timezone.utc)


def _proposal() -> ProposalRecord:
    return ProposalRecord(
        proposal_id="pp_version_read",
        portfolio_id="pf_version_read",
        mandate_id="mandate_version_read",
        jurisdiction="SG",
        created_by="advisor_version_read",
        created_at=_now(),
        last_event_at=_now(),
        current_state="DRAFT",
        current_version_no=2,
        title="Version read model proposal",
    )


def _version(*, version_no: int) -> ProposalVersionRecord:
    return ProposalVersionRecord(
        proposal_version_id=f"ppv_version_read_{version_no}",
        proposal_id="pp_version_read",
        version_no=version_no,
        created_at=_now(),
        request_hash=f"sha256:req-version-read-{version_no}",
        artifact_hash=f"sha256:artifact-version-read-{version_no}",
        simulation_hash=f"sha256:sim-version-read-{version_no}",
        status_at_creation="READY",
        proposal_result_json={"status": "READY"},
        artifact_json={},
        evidence_bundle_json={},
        gate_decision_json=None,
    )


def test_load_proposal_version_read_model_returns_requested_version():
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal())
    repository.create_version(_version(version_no=1))
    repository.create_version(_version(version_no=2))

    read_model = load_proposal_version_read_model(
        repository=repository,
        proposal_id="pp_version_read",
        version_no=2,
    )

    assert read_model.version is not None
    assert read_model.version.proposal_version_id == "ppv_version_read_2"


def test_load_proposal_version_read_model_preserves_missing_version_boundary():
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal())

    read_model = load_proposal_version_read_model(
        repository=repository,
        proposal_id="pp_version_read",
        version_no=99,
    )

    assert read_model.version is None
