from fastapi.testclient import TestClient

from src.api.main import PROPOSAL_IDEMPOTENCY_CACHE, app
from src.api.proposals.router import reset_proposal_workflow_service_for_tests


def setup_function() -> None:
    PROPOSAL_IDEMPOTENCY_CACHE.clear()
    reset_proposal_workflow_service_for_tests()


def _base_create_payload(portfolio_id: str = "pf_memo_api_1") -> dict:
    return {
        "created_by": "advisor_1",
        "metadata": {
            "title": "Memo API proposal",
            "advisor_notes": "Advisor notes",
            "jurisdiction": "SG",
            "mandate_id": "mandate_1",
        },
        "simulate_request": {
            "portfolio_snapshot": {
                "portfolio_id": portfolio_id,
                "base_currency": "USD",
                "positions": [{"instrument_id": "EQ_OLD", "quantity": "10"}],
                "cash_balances": [{"currency": "USD", "amount": "1000"}],
            },
            "market_data_snapshot": {
                "prices": [
                    {
                        "instrument_id": "EQ_OLD",
                        "price": "100",
                        "currency": "USD",
                        "valid_to": "3999-12-31",
                    },
                    {
                        "instrument_id": "EQ_NEW",
                        "price": "50",
                        "currency": "USD",
                        "valid_to": "3999-12-31",
                    },
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
        },
    }


def _create_proposal(client: TestClient) -> dict:
    response = client.post(
        "/advisory/proposals",
        json=_base_create_payload(),
        headers={"Idempotency-Key": "memo-api-proposal-create"},
    )
    assert response.status_code == 200
    return response.json()


def _create_memo(client: TestClient, proposal_id: str) -> dict:
    response = client.post(
        f"/advisory/proposals/{proposal_id}/versions/1/memo",
        json={"created_by": "advisor_1", "reason": {"purpose": "advisor review"}},
        headers={"Idempotency-Key": "memo-api-create"},
    )
    assert response.status_code == 200
    return response.json()


def test_proposal_memo_api_create_read_project_lineage_and_replay() -> None:
    with TestClient(app) as client:
        created = _create_proposal(client)
        proposal_id = created["proposal"]["proposal_id"]

        memo = _create_memo(client, proposal_id)
        assert memo["proposal"]["proposal_id"] == proposal_id
        assert memo["proposal_version_no"] == 1
        assert memo["memo_id"].startswith("memo_")
        assert memo["memo_status"] in {"BLOCKED", "PENDING_REVIEW", "READY"}
        assert memo["lifecycle_status"] == "DRAFT"
        assert memo["projection"]["client_ready_publication"] == "BLOCKED"
        assert memo["memo"]["supportability"]["persistence"] == "SUPPORTED_BY_RFC0024_SLICE6"
        assert memo["memo"]["supportability"]["api"] == "SUPPORTED_BY_RFC0024_SLICE7"
        assert (
            memo["memo"]["supportability"]["policy_fee_conflict_enrichment"]
            == "SUPPORTED_BY_RFC0024_SLICE8"
        )
        assert memo["read_posture"]["gateway_supported"] is False
        assert memo["event_count"] == 1
        assert memo["audit_events"][0]["event_type"] == "MEMO_DRAFT_CREATED"
        assert memo["audit_events"][0]["reason"]["creation_reason"] == {"purpose": "advisor review"}
        assert memo["replay_metadata"]["creation_reason"] == {"purpose": "advisor review"}
        assert memo["replay_metadata"]["proposal_artifact_hash"].startswith("sha256:")

        replayed_create = client.post(
            f"/advisory/proposals/{proposal_id}/versions/1/memo",
            json={"created_by": "advisor_1", "reason": {"purpose": "advisor review"}},
            headers={"Idempotency-Key": "memo-api-create"},
        )
        assert replayed_create.status_code == 200
        assert replayed_create.json()["memo_id"] == memo["memo_id"]
        assert replayed_create.json()["event_count"] == 1

        drifted_create = client.post(
            f"/advisory/proposals/{proposal_id}/versions/1/memo",
            json={"created_by": "advisor_1", "reason": {"purpose": "different"}},
            headers={"Idempotency-Key": "memo-api-create"},
        )
        assert drifted_create.status_code == 409
        assert "MEMO_IDEMPOTENCY_KEY_CONFLICT" in drifted_create.json()["detail"]

        read = client.get(f"/advisory/proposals/{proposal_id}/versions/1/memo")
        assert read.status_code == 200
        assert read.json()["memo_hash"] == memo["memo_hash"]

        projection = client.get(
            f"/advisory/proposals/{proposal_id}/versions/1/memo/projection",
            params={"audience": "ADVISOR"},
        )
        assert projection.status_code == 200
        projection_body = projection.json()
        assert projection_body["memo_id"] == memo["memo_id"]
        assert projection_body["projection_posture"]["mutation_performed"] is False
        assert projection_body["projection_posture"]["client_ready_publication"] == "BLOCKED"
        assert projection_body["sections"]
        assert all(
            "ADVISOR" in section["audience_visibility"] for section in projection_body["sections"]
        )

        lineage = client.get(f"/advisory/proposals/{proposal_id}/memos/lineage")
        assert lineage.status_code == 200
        lineage_body = lineage.json()
        assert lineage_body["memo_count"] == 1
        assert lineage_body["latest_memo_id"] == memo["memo_id"]
        assert lineage_body["lineage_complete"] is True

        replay = client.get(f"/advisory/proposals/{proposal_id}/versions/1/memo/replay-evidence")
        assert replay.status_code == 200
        replay_body = replay.json()
        assert replay_body["subject"]["memo_id"] == memo["memo_id"]
        assert replay_body["hashes"]["memo_hash"] == memo["memo_hash"]
        assert replay_body["explanation"]["client_ready_publication"] == "BLOCKED"


def test_proposal_memo_review_and_report_package_events_are_idempotent_and_hash_guarded() -> None:
    with TestClient(app) as client:
        created = _create_proposal(client)
        proposal_id = created["proposal"]["proposal_id"]
        memo = _create_memo(client, proposal_id)

        review_payload = {
            "action": "APPROVE_FOR_ADVISOR_USE",
            "reviewed_by": "compliance_1",
            "reason": "Evidence is sufficient for advisor discussion.",
            "source_memo_hash": memo["memo_hash"],
        }
        review = client.post(
            f"/advisory/proposals/{proposal_id}/versions/1/memo/review",
            json=review_payload,
            headers={"Idempotency-Key": "memo-review-1"},
        )
        assert review.status_code == 200
        review_body = review.json()
        assert review_body["replayed"] is False
        assert review_body["review_event"]["event_type"] == "MEMO_REVIEW_RECORDED"
        assert review_body["memo"]["review_posture"]["review_action"] == "APPROVE_FOR_ADVISOR_USE"

        replayed_review = client.post(
            f"/advisory/proposals/{proposal_id}/versions/1/memo/review",
            json=review_payload,
            headers={"Idempotency-Key": "memo-review-1"},
        )
        assert replayed_review.status_code == 200
        assert replayed_review.json()["replayed"] is True
        assert (
            replayed_review.json()["review_event"]["event_id"]
            == (review_body["review_event"]["event_id"])
        )

        drifted_review = dict(review_payload)
        drifted_review["reason"] = "Different review reason"
        conflict = client.post(
            f"/advisory/proposals/{proposal_id}/versions/1/memo/review",
            json=drifted_review,
            headers={"Idempotency-Key": "memo-review-1"},
        )
        assert conflict.status_code == 409
        assert "MEMO_EVENT_IDEMPOTENCY_KEY_CONFLICT" in conflict.json()["detail"]

        stale = client.post(
            f"/advisory/proposals/{proposal_id}/versions/1/memo/review",
            json={**review_payload, "source_memo_hash": "sha256:stale"},
        )
        assert stale.status_code == 422
        assert stale.json()["detail"] == "MEMO_SOURCE_HASH_MISMATCH"

        client_ready = client.post(
            f"/advisory/proposals/{proposal_id}/versions/1/memo/review",
            json={**review_payload, "client_ready_release_requested": True},
        )
        assert client_ready.status_code == 422
        assert client_ready.json()["detail"] == "MEMO_CLIENT_READY_RELEASE_NOT_SUPPORTED"

        report_event = client.post(
            f"/advisory/proposals/{proposal_id}/versions/1/memo/report-package-events",
            json={
                "recorded_by": "ops_1",
                "report_package_id": "memo_report_package_001",
                "report_package_status": "BLOCKED",
                "source_memo_hash": memo["memo_hash"],
                "reason": {"blocked_by": "CLIENT_READY_MEMO_NOT_SUPPORTED"},
            },
            headers={"Idempotency-Key": "memo-report-event-1"},
        )
        assert report_event.status_code == 200
        report_body = report_event.json()
        assert report_body["replayed"] is False
        assert report_body["report_package_event"]["event_type"] == "MEMO_REPORT_PACKAGE_RECORDED"
        assert report_body["memo"]["report_package_posture"]["report_package_status"] == "BLOCKED"

        replay = client.get(f"/advisory/proposals/{proposal_id}/versions/1/memo/replay-evidence")
        assert replay.status_code == 200
        replay_body = replay.json()
        event_types = [event["event_type"] for event in replay_body["audit_events"]]
        assert event_types == [
            "MEMO_DRAFT_CREATED",
            "MEMO_REVIEW_RECORDED",
            "MEMO_REPORT_PACKAGE_RECORDED",
        ]


def test_memo_api_blocks_finalization_until_source_ready_and_reports_missing_memo() -> None:
    with TestClient(app) as client:
        created = _create_proposal(client)
        proposal_id = created["proposal"]["proposal_id"]

        missing = client.get(f"/advisory/proposals/{proposal_id}/versions/1/memo")
        assert missing.status_code == 404
        assert missing.json()["detail"] == "PROPOSAL_MEMO_NOT_FOUND"

        finalized = client.post(
            f"/advisory/proposals/{proposal_id}/versions/1/memo",
            json={"created_by": "advisor_1", "lifecycle_status": "FINALIZED"},
            headers={"Idempotency-Key": "memo-finalized-blocked"},
        )
        assert finalized.status_code == 422
        assert finalized.json()["detail"] == "MEMO_FINALIZATION_BLOCKED_BY_EVIDENCE_POSTURE"
