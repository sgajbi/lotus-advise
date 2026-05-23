import httpx
import pytest

from src.integrations.lotus_report.adapter import (
    LotusReportUnavailableError,
    _resolve_timeout,
    request_proposal_report_with_lotus_report,
)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload
        self.request = httpx.Request("POST", "http://report.dev.lotus/reports/portfolio-reviews")

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "report unavailable",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response
        self.posts: list[dict] = []

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def post(self, url: str, *, json: dict, headers: dict[str, str]) -> _FakeResponse:
        self.posts.append({"url": url, "json": json, "headers": headers})
        return self.response


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
        "proposal_version": {
            "proposal_result": {
                "before": {"total_value": {"amount": "100.00", "currency": "USD"}},
                "analytics": {"metadata": {"as_of_date": "2026-04-10"}},
            }
        },
        "report_type": "PORTFOLIO_REVIEW",
        "requested_by": "advisor_1",
        "related_version_no": 1,
        "include_execution_summary": True,
        "include_reviewed_narrative": True,
        "proposal_narrative_package": {
            "package_status": "INCLUDED_REVIEWED_NARRATIVE",
            "usage": "REPORT_REQUEST_APPROVED_ADVISOR_NARRATIVE",
            "proposal_id": "pp_live_001",
            "proposal_version_no": 1,
            "narrative_id": "pnar_live_001",
            "review": {"review_state": "APPROVED_FOR_ADVISOR_USE"},
            "source_lineage": {"source_narrative_hash": "sha256:narrative"},
            "sections": [
                {
                    "section_id": "executive_summary",
                    "title": "Executive Summary",
                    "body": "Advisor-reviewed narrative.",
                }
            ],
        },
    }


def test_lotus_report_adapter_submits_portfolio_review_job_with_reviewed_narrative(
    monkeypatch,
) -> None:
    fake_client = _FakeClient(
        _FakeResponse(
            202,
            {
                "report_request_id": "rrq_report_001",
                "report_job_id": "rjob_report_001",
                "status": "data_ready",
                "status_url": "/reports/jobs/rjob_report_001",
                "idempotency_key": "prr_live_001",
            },
        )
    )
    monkeypatch.setenv("LOTUS_REPORT_BASE_URL", "http://report.dev.lotus/")
    monkeypatch.setattr(
        "src.integrations.lotus_report.adapter.httpx.Client",
        lambda timeout: fake_client,
    )

    response = request_proposal_report_with_lotus_report(request=_proposal_request())

    assert response.status == "READY"
    assert response.report_request_id == "prr_live_001"
    assert response.report_reference_id == "rjob_report_001"
    assert response.explanation["proposal_narrative_package"] == {
        "package_status": "INCLUDED_REVIEWED_NARRATIVE",
        "narrative_id": "pnar_live_001",
        "review_state": "APPROVED_FOR_ADVISOR_USE",
        "source_narrative_hash": "sha256:narrative",
    }
    [post] = fake_client.posts
    assert post["url"] == "http://report.dev.lotus/reports/portfolio-reviews"
    assert post["headers"]["Idempotency-Key"] == "prr_live_001"
    assert post["headers"]["X-Caller-Application"] == "lotus-advise"
    assert post["json"]["portfolio_scope"] == {"portfolio_ids": ["PB_SG_GLOBAL_BAL_001"]}
    assert post["json"]["as_of_date"] == "2026-04-10"
    assert post["json"]["requested_output_formats"] == ["json"]
    assert post["json"]["proposal_narrative_package"]["narrative_id"] == "pnar_live_001"


def test_lotus_report_adapter_fails_closed_when_report_base_url_is_missing(monkeypatch) -> None:
    monkeypatch.delenv("LOTUS_REPORT_BASE_URL", raising=False)

    with pytest.raises(LotusReportUnavailableError, match="LOTUS_REPORT_REQUEST_UNAVAILABLE"):
        request_proposal_report_with_lotus_report(request=_proposal_request())


def test_lotus_report_timeout_defaults_to_report_job_acceptance_sla(monkeypatch) -> None:
    monkeypatch.delenv("LOTUS_REPORT_TIMEOUT_SECONDS", raising=False)

    timeout = _resolve_timeout()

    assert timeout.connect == 30.0
    assert timeout.read == 30.0


def test_lotus_report_timeout_uses_positive_override(monkeypatch) -> None:
    monkeypatch.setenv("LOTUS_REPORT_TIMEOUT_SECONDS", "45")

    timeout = _resolve_timeout()

    assert timeout.connect == 45.0
    assert timeout.read == 45.0
