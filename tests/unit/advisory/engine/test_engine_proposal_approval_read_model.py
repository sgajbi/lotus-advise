from datetime import datetime, timezone

from src.core.proposals.approval_read_model import load_proposal_approval_read_model
from src.core.proposals.models import ProposalApprovalRecordData, ProposalRecord
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime(2026, 5, 21, 12, 0, tzinfo=timezone.utc)


def _proposal() -> ProposalRecord:
    return ProposalRecord(
        proposal_id="pp_approval_read",
        portfolio_id="pf_approval_read",
        mandate_id="mandate_approval_read",
        jurisdiction="SG",
        created_by="advisor_approval_read",
        created_at=_now(),
        last_event_at=_now(),
        current_state="AWAITING_CLIENT_CONSENT",
        current_version_no=1,
        title="Approval read-model proposal",
    )


def _approval(approval_id: str, approval_type: str) -> ProposalApprovalRecordData:
    return ProposalApprovalRecordData(
        approval_id=approval_id,
        proposal_id="pp_approval_read",
        approval_type=approval_type,
        approved=True,
        actor_id="approver_approval_read",
        occurred_at=_now(),
        details_json={"decision": "approved"},
        related_version_no=1,
    )


def test_load_proposal_approval_read_model_returns_proposal_and_approvals():
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal())
    repository.create_approval(_approval("pap_approval_read_1", "COMPLIANCE"))
    repository.create_approval(_approval("pap_approval_read_2", "CLIENT_CONSENT"))

    read_model = load_proposal_approval_read_model(
        repository=repository,
        proposal_id="pp_approval_read",
    )

    assert read_model.proposal is not None
    assert read_model.proposal.proposal_id == "pp_approval_read"
    assert [approval.approval_id for approval in read_model.approvals] == [
        "pap_approval_read_1",
        "pap_approval_read_2",
    ]


def test_load_proposal_approval_read_model_preserves_missing_proposal_boundary():
    read_model = load_proposal_approval_read_model(
        repository=InMemoryProposalRepository(),
        proposal_id="pp_missing",
    )

    assert read_model.proposal is None
    assert read_model.approvals == []
