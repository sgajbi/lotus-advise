from datetime import datetime, timezone

from src.core.proposals.models import ProposalRecord, ProposalReportResponse
from src.core.proposals.projections import to_proposal_summary
from src.core.proposals.reporting import build_report_requested_event


def test_build_report_requested_event_preserves_report_lineage_payload():
    proposal = ProposalRecord(
        proposal_id="pp_report_projection",
        portfolio_id="pf_report_projection",
        mandate_id="mandate_report_projection",
        jurisdiction="SG",
        created_by="advisor_report_projection",
        created_at=datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc),
        last_event_at=datetime(2026, 5, 20, 9, 5, tzinfo=timezone.utc),
        current_state="EXECUTION_READY",
        current_version_no=3,
        title="Report projection proposal",
    )
    report_response = ProposalReportResponse(
        proposal=to_proposal_summary(proposal),
        report_request_id="prr_projection",
        report_type="CLIENT_PROPOSAL_SUMMARY",
        report_service="lotus-report",
        status="READY",
        report_reference_id="rpt_projection",
        artifact_url="https://reports.example/client-advisory-pack.pdf",
        generated_at="2026-05-20T09:10:00+00:00",
    )

    event = build_report_requested_event(
        event_id="pwe_report_projection",
        proposal=proposal,
        report_response=report_response,
        requested_by="advisor_report_projection",
        related_version_no=3,
        include_execution_summary=True,
    )

    assert event.model_dump(mode="json") == {
        "event_id": "pwe_report_projection",
        "proposal_id": "pp_report_projection",
        "event_type": "REPORT_REQUESTED",
        "from_state": "EXECUTION_READY",
        "to_state": "EXECUTION_READY",
        "actor_id": "advisor_report_projection",
        "occurred_at": "2026-05-20T09:10:00Z",
        "reason_json": {
            "report_request_id": "prr_projection",
            "report_type": "CLIENT_PROPOSAL_SUMMARY",
            "report_service": "lotus-report",
            "status": "READY",
            "report_reference_id": "rpt_projection",
            "artifact_url": "https://reports.example/client-advisory-pack.pdf",
            "related_version_no": 3,
            "include_execution_summary": True,
        },
        "related_version_no": 3,
    }
