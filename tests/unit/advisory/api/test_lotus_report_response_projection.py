import pytest

from src.integrations.lotus_report.request_mapping import LotusReportRequestMappingError
from src.integrations.lotus_report.response_projection import (
    build_memo_report_package_response,
    build_policy_sign_off_report_package_response,
    build_portfolio_review_response,
)


def _proposal_request() -> dict:
    return {
        "report_request_id": "prr_live_001",
        "proposal": {
            "proposal_id": "pp_live_001",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "jurisdiction": "SG",
            "created_by": "advisor_1",
            "created_at": "2026-05-23T00:00:00Z",
            "last_event_at": "2026-05-23T00:01:00Z",
            "current_state": "DRAFT",
            "current_version_no": 1,
            "lifecycle_origin": "DIRECT_CREATE",
        },
        "requested_by": "advisor_1",
        "related_version_no": 1,
        "include_execution_summary": True,
        "include_reviewed_narrative": True,
    }


def _report_job_request() -> dict:
    return {
        "portfolio_scope": {"portfolio_ids": ["PB_SG_GLOBAL_BAL_001"]},
        "as_of_date": "2026-04-10",
        "requested_output_formats": ["json"],
        "reporting_currency": "USD",
    }


def test_portfolio_review_projection_keeps_reviewed_narrative_summary_bounded() -> None:
    request = _proposal_request()
    request["proposal_narrative_package"] = {
        "package_status": "INCLUDED_REVIEWED_NARRATIVE",
        "narrative_id": "pnar_live_001",
        "review": {"review_state": "APPROVED_FOR_ADVISOR_USE"},
        "source_lineage": {"source_narrative_hash": "sha256:narrative"},
        "sections": [{"body": "Full advisor narrative stays in the report handoff payload."}],
    }

    response = build_portfolio_review_response(
        request=request,
        request_id="prr_live_001",
        report_type="PORTFOLIO_REVIEW",
        report_job_request=_report_job_request(),
        response_payload={
            "report_job_id": "rjob_report_001",
            "status": "data_ready",
            "status_url": "/reports/jobs/rjob_report_001",
            "idempotency_key": "prr_live_001",
        },
    )

    assert response.status == "READY"
    assert response.artifact_url == "/reports/jobs/rjob_report_001"
    assert response.explanation["proposal_narrative_package"] == {
        "package_status": "INCLUDED_REVIEWED_NARRATIVE",
        "narrative_id": "pnar_live_001",
        "review_state": "APPROVED_FOR_ADVISOR_USE",
        "source_narrative_hash": "sha256:narrative",
    }
    assert "sections" not in response.explanation["proposal_narrative_package"]


def test_memo_and_policy_projection_preserve_blocked_client_ready_boundary() -> None:
    memo_request = _proposal_request()
    memo_request["proposal_memo_package"] = {
        "package_status": "INCLUDED_ADVISOR_PROPOSAL_MEMO",
        "memo_id": "memo_001",
        "memo_hash": "sha256:memo",
        "review": {"review_action": "APPROVE_FOR_ADVISOR_USE"},
    }
    policy_request = _proposal_request()
    policy_request["related_policy_evaluation_id"] = "pev_policy_001"
    policy_request["policy_sign_off_package"] = {
        "package_status": "SIGNED_OFF_SOURCE_PACKAGE",
        "evaluation": {
            "evaluation_id": "pev_policy_001",
            "evaluation_hash": "sha256:policy-evaluation",
        },
    }

    memo_response = build_memo_report_package_response(
        request=memo_request,
        request_id="prr_memo_001",
        report_job_request=_report_job_request(),
        response_payload={"report_job_id": "rjob_memo_001", "status": "accepted"},
        status_payload={
            "status": "archived",
            "render": {"render_job_id": "rdr_memo_001"},
            "archive": {"document_id": "doc_memo_001"},
        },
    )
    policy_response = build_policy_sign_off_report_package_response(
        request=policy_request,
        request_id="prr_policy_001",
        report_job_request=_report_job_request(),
        response_payload={"report_job_id": "rjob_policy_001", "status": "accepted"},
        status_payload={
            "status": "archived",
            "render": {"render_job_id": "rdr_policy_001"},
            "archive": {"document_id": "doc_policy_001"},
        },
    )

    assert memo_response.status == "ARCHIVED"
    assert (
        memo_response.explanation["proposal_memo_package"]["client_ready_publication"] == "BLOCKED"
    )
    assert memo_response.explanation["render"] == {"render_job_id": "rdr_memo_001"}
    assert policy_response.status == "ARCHIVED"
    assert policy_response.explanation["policy_sign_off_package"] == {
        "package_status": "SIGNED_OFF_SOURCE_PACKAGE",
        "evaluation_id": "pev_policy_001",
        "evaluation_hash": "sha256:policy-evaluation",
        "client_ready_publication": "BLOCKED",
    }


def test_projection_fails_closed_when_report_response_identity_is_missing() -> None:
    with pytest.raises(
        LotusReportRequestMappingError,
        match="LOTUS_REPORT_REQUEST_UNAVAILABLE",
    ):
        build_memo_report_package_response(
            request=_proposal_request(),
            request_id="prr_memo_001",
            report_job_request=_report_job_request(),
            response_payload={"status": "accepted"},
            status_payload={},
        )


def test_projection_fails_closed_when_report_response_idempotency_key_mismatches() -> None:
    with pytest.raises(
        LotusReportRequestMappingError,
        match="LOTUS_REPORT_REQUEST_UNAVAILABLE",
    ):
        build_memo_report_package_response(
            request=_proposal_request(),
            request_id="prr_memo_001",
            report_job_request=_report_job_request(),
            response_payload={
                "report_job_id": "rjob_memo_001",
                "status": "accepted",
                "idempotency_key": "prr_other_request",
            },
            status_payload={},
        )
