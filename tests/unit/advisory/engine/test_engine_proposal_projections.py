from datetime import datetime, timezone

from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalCreateRequest,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.projections import (
    to_approval_record,
    to_proposal_summary,
    to_version_detail,
    to_workflow_event,
)
from src.core.proposals.service import ProposalWorkflowService
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _simulate_request(portfolio_id: str = "pf_projection") -> dict:
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


def test_to_proposal_summary_preserves_lifecycle_identity():
    proposal = ProposalRecord(
        proposal_id="pp_projection",
        portfolio_id="pf_projection",
        mandate_id="mandate_projection",
        jurisdiction="SG",
        created_by="advisor_projection",
        created_at=datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc),
        last_event_at=datetime(2026, 5, 20, 9, 5, tzinfo=timezone.utc),
        current_state="DRAFT",
        current_version_no=1,
        title="Projection test proposal",
        lifecycle_origin="WORKSPACE_HANDOFF",
        source_workspace_id="aws_projection",
    )

    summary = to_proposal_summary(proposal)

    assert summary.model_dump(mode="json") == {
        "proposal_id": "pp_projection",
        "portfolio_id": "pf_projection",
        "mandate_id": "mandate_projection",
        "jurisdiction": "SG",
        "created_by": "advisor_projection",
        "created_at": "2026-05-20T09:00:00+00:00",
        "last_event_at": "2026-05-20T09:05:00+00:00",
        "current_state": "DRAFT",
        "current_version_no": 1,
        "title": "Projection test proposal",
        "lifecycle_origin": "WORKSPACE_HANDOFF",
        "source_workspace_id": "aws_projection",
    }


def test_to_version_detail_can_omit_evidence_bundle():
    repository = InMemoryProposalRepository()
    service = ProposalWorkflowService(repository=repository)
    created = service.create_proposal(
        payload=ProposalCreateRequest(
            created_by="advisor_projection",
            simulate_request=_simulate_request(),
        ),
        idempotency_key="idem_projection",
        correlation_id="corr_projection",
    )
    version = repository.get_version(
        proposal_id=created.proposal.proposal_id,
        version_no=created.version.version_no,
    )
    assert version is not None

    without_evidence = to_version_detail(version, include_evidence=False)
    with_evidence = to_version_detail(version, include_evidence=True)

    assert without_evidence.evidence_bundle == {}
    assert with_evidence.evidence_bundle == version.evidence_bundle_json
    assert with_evidence.gate_decision.model_dump(mode="json") == version.gate_decision_json


def test_to_workflow_event_and_approval_record_preserve_audit_payloads():
    event = ProposalWorkflowEventRecord(
        event_id="pwe_projection",
        proposal_id="pp_projection",
        event_type="CLIENT_CONSENT_RECORDED",
        from_state="AWAITING_CLIENT_CONSENT",
        to_state="EXECUTION_READY",
        actor_id="client_projection",
        occurred_at=datetime(2026, 5, 20, 9, 15, tzinfo=timezone.utc),
        reason_json={"channel": "IN_PERSON"},
        related_version_no=2,
    )
    approval = ProposalApprovalRecordData(
        approval_id="pap_projection",
        proposal_id="pp_projection",
        approval_type="CLIENT_CONSENT",
        approved=True,
        actor_id="client_projection",
        occurred_at=datetime(2026, 5, 20, 9, 16, tzinfo=timezone.utc),
        details_json={"channel": "IN_PERSON"},
        related_version_no=2,
    )

    projected_event = to_workflow_event(event)
    projected_approval = to_approval_record(approval)

    assert projected_event.reason == {"channel": "IN_PERSON"}
    assert projected_event.occurred_at == "2026-05-20T09:15:00+00:00"
    assert projected_approval is not None
    assert projected_approval.details == {"channel": "IN_PERSON"}
    assert projected_approval.occurred_at == "2026-05-20T09:16:00+00:00"
    assert to_approval_record(None) is None
