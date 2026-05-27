from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient

import src.api.main as api_main
import src.core.policy_packs.ai as policy_ai
from src.api.main import app
from src.core.policy_packs import (
    get_policy_pack_version,
    reset_policy_evaluation_store_for_tests,
    reset_policy_pack_catalog_for_tests,
)
from src.integrations.lotus_ai.policy_evidence import PolicyAiEvidenceDraft


def setup_function() -> None:
    if hasattr(api_main, "request_policy_sign_off_report_package_with_lotus_report"):
        delattr(api_main, "request_policy_sign_off_report_package_with_lotus_report")
    reset_policy_pack_catalog_for_tests()
    reset_policy_evaluation_store_for_tests()


def _base_evidence_bundle() -> dict:
    return {
        "context_resolution": {
            "advisory_policy_context": {
                "household_id": "HH-PB-001",
                "jurisdiction": "SG",
                "client_classification": "ACCREDITED_INVESTOR",
                "booking_center_code": "SG",
                "account_id": "ACCT-PB-001",
                "time_horizon": "5Y",
                "liquidity_need": "MEDIUM",
                "mandate_id": "MANDATE-BALANCED-001",
                "objectives": ["capital_preservation", "balanced_growth"],
                "restrictions": ["no_single_name_above_10pct"],
            }
        },
        "inputs": {
            "portfolio_snapshot": {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "positions": [{"instrument_id": "US_EQ_ETF", "quantity": "100"}],
                "cash_balances": [{"currency": "USD", "amount": "50000"}],
            },
            "market_data_snapshot": {
                "prices": [{"instrument_id": "US_EQ_ETF", "price": "100", "currency": "USD"}],
                "fx_rates": [{"pair": "USD/SGD", "rate": "1.35"}],
            },
            "shelf_entries": [
                {
                    "instrument_id": "US_EQ_ETF",
                    "eligibility": {"jurisdictions": ["SG"]},
                    "target_market": {"client_segments": ["ACCREDITED_INVESTOR"]},
                    "complexity": "NON_COMPLEX",
                    "private_asset": False,
                    "structured_product": False,
                }
            ],
            "proposed_trades": [{"instrument_id": "US_EQ_ETF", "side": "BUY"}],
        },
        "risk_lens": {
            "source_service": "lotus-risk",
            "single_position_concentration": {"top_position_weight_current": "0.10"},
            "issuer_concentration": {"hhi_current": "1200"},
            "drawdown": {"max_drawdown_1y": "0.08"},
            "var": {"var_95_1m": "0.04"},
            "stress": {"equity_down_20": "-0.09"},
            "liquidity_risk": {"days_to_liquidate": "3"},
            "private_asset_risk": {"private_asset_weight": "0.00"},
            "climate_geopolitical_risk": {"status": "not_material"},
        },
        "artifact": {
            "assumptions_and_limits": {
                "costs_and_fees": {"included": True},
                "tax": {"included": True},
                "execution": {"included": True},
            },
            "disclosures": {
                "product_docs": [{"instrument_id": "US_EQ_ETF", "doc_ref": "Factsheet"}],
            },
        },
        "conflict_evidence": {"material_conflict": False, "review_ref": "conflict-review-001"},
    }


def _create_payload(evidence: dict | None = None) -> dict:
    return {
        "policy_pack_id": "GLOBAL_PRIVATE_BANKING_BASELINE",
        "policy_version": "2026.05",
        "created_by": "advisor_1",
        "evidence_bundle": evidence or _base_evidence_bundle(),
        "reason": {"purpose": "advisor suitability review"},
    }


def _activate_sg_pack(client: TestClient) -> None:
    content_hash = get_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
    ).policy_pack.content_hash
    validated = client.post(
        "/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05/validate",
        json={"requested_by": "policy_steward_1", "reason": {"purpose": "api test"}},
        headers={"Idempotency-Key": "api-policy-eval-validate-sg"},
    )
    assert validated.status_code == 200
    activated = client.post(
        "/advisory/policy-packs/SG_PRIVATE_BANKING_REFERENCE/versions/2026.05/activate",
        json={
            "activated_by": "policy_checker_1",
            "source_content_hash": content_hash,
            "reason": {"purpose": "api test"},
        },
        headers={"Idempotency-Key": "api-policy-eval-activate-sg"},
    )
    assert activated.status_code == 200


def _sg_pending_payload() -> dict:
    evidence = _base_evidence_bundle()
    evidence["inputs"]["shelf_entries"][0]["instrument_id"] = "SG_STRUCTURED_NOTE"
    evidence["inputs"]["shelf_entries"][0]["complexity"] = "COMPLEX"
    evidence["inputs"]["shelf_entries"][0]["structured_product"] = True
    evidence["inputs"]["proposed_trades"][0]["instrument_id"] = "SG_STRUCTURED_NOTE"
    evidence["artifact"]["disclosures"]["product_docs"] = [
        {"instrument_id": "SG_STRUCTURED_NOTE", "doc_ref": "Term sheet"}
    ]
    payload = _create_payload(evidence)
    payload["policy_pack_id"] = "SG_PRIVATE_BANKING_REFERENCE"
    return payload


def test_policy_evaluation_api_finalizes_reads_replays_and_records_events() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/advisory/proposals/pp_policy_api_001/versions/ppv_policy_api_001/policy-evaluations",
            json=_create_payload(),
            headers={"Idempotency-Key": "api-policy-eval-create-001"},
        )
        assert created.status_code == 200
        created_body = created.json()
        evaluation_id = created_body["record"]["evaluation_id"]

        replayed = client.post(
            "/advisory/proposals/pp_policy_api_001/versions/ppv_policy_api_001/policy-evaluations",
            json=_create_payload(),
            headers={"Idempotency-Key": "api-policy-eval-create-001"},
        )
        assert replayed.status_code == 200
        assert replayed.json()["replayed"] is True

        drift = client.post(
            "/advisory/proposals/pp_policy_api_001/versions/ppv_policy_api_001/policy-evaluations",
            json={**_create_payload(), "reason": {"purpose": "changed"}},
            headers={"Idempotency-Key": "api-policy-eval-create-001"},
        )
        assert drift.status_code == 409

        read = client.get(f"/advisory/policy-evaluations/{evaluation_id}")
        assert read.status_code == 200
        read_body = read.json()
        assert read_body["evaluation_hash"].startswith("sha256:")
        assert read_body["evaluation_json"]["supportability"]["policy_evaluation_api"] == (
            "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API"
        )
        assert read_body["evaluation_json"]["supportability"]["gateway_supported"] is True
        assert read_body["evaluation_json"]["supportability"]["gateway_support"] == (
            "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_BFF"
        )
        assert read_body["evaluation_json"]["supportability"]["active_data_product_promotion"] == (
            "SUPPORTED_BY_RFC0025_SLICE16_FINAL_CLOSURE"
        )

        replay = client.post(
            f"/advisory/policy-evaluations/{evaluation_id}/replay",
            json={"evidence_bundle": _base_evidence_bundle()},
        )
        assert replay.status_code == 200
        assert replay.json()["hash_comparison"]["evaluation_hash_matches"] is True

        changed_evidence = deepcopy(_base_evidence_bundle())
        changed_evidence["inputs"]["market_data_snapshot"]["fx_rates"][0]["rate"] = "1.36"
        changed = client.post(
            f"/advisory/policy-evaluations/{evaluation_id}/replay",
            json={"evidence_bundle": changed_evidence},
        )
        assert changed.status_code == 200
        assert changed.json()["hash_comparison"]["source_evidence_hash_matches"] is False

        review = client.post(
            f"/advisory/policy-evaluations/{evaluation_id}/events",
            json={
                "event_type": "POLICY_EVALUATION_REVIEW_RECORDED",
                "actor_id": "compliance_1",
                "reason": {"review_action": "REQUEST_MORE_EVIDENCE"},
            },
            headers={"Idempotency-Key": "api-policy-eval-review-001"},
        )
        assert review.status_code == 200
        assert review.json()["event_type"] == "POLICY_EVALUATION_REVIEW_RECORDED"

        lineage = client.get(f"/advisory/policy-evaluations/{evaluation_id}/lineage")
        assert lineage.status_code == 200
        lineage_body = lineage.json()
        assert [event["event_type"] for event in lineage_body["audit_events"]] == [
            "POLICY_EVALUATION_FINALIZED",
            "POLICY_EVALUATION_REVIEW_RECORDED",
        ]
        assert lineage_body["lineage_posture"]["client_ready_publication"] == "BLOCKED"

        sign_off = client.get(f"/advisory/policy-evaluations/{evaluation_id}/sign-off-package")
        assert sign_off.status_code == 200
        sign_off_body = sign_off.json()
        assert sign_off_body["evaluation"]["evaluation_id"] == evaluation_id
        assert sign_off_body["package_posture"]["report_render_archive_realization"] == (
            "SUPPORTED_BY_RFC0025_SLICE10_SIGNED_OFF_PACKAGE_HANDOFF"
        )
        assert sign_off_body["package_posture"]["client_ready_publication"] == "BLOCKED"


def test_policy_evaluation_workflow_and_sign_off_decision_api_enforce_requirements() -> None:
    with TestClient(app) as client:
        _activate_sg_pack(client)
        created = client.post(
            "/advisory/proposals/pp_policy_signoff_001/versions/ppv_policy_signoff_001/policy-evaluations",
            json=_sg_pending_payload(),
            headers={"Idempotency-Key": "api-policy-eval-signoff-001"},
        )
        assert created.status_code == 200
        record = created.json()["record"]
        evaluation_id = record["evaluation_id"]

        workflow = client.get(f"/advisory/policy-evaluations/{evaluation_id}/workflow")
        assert workflow.status_code == 200
        workflow_body = workflow.json()
        assert workflow_body["sign_off_status"] == "PENDING_REVIEW"
        assert workflow_body["client_ready_publication"] == "BLOCKED"
        assert workflow_body["sla_posture"]["open_requirement_count"] >= 3
        assert workflow_body["approval_dependencies"][0]["requirement_id"] == (
            "REVIEW_DISCLOSURE:SG_STRUCTURED_NOTE"
        )

        blocked = client.post(
            f"/advisory/policy-evaluations/{evaluation_id}/sign-off-decisions",
            json={
                "actor_id": "policy_checker_1",
                "decision": "APPROVE_FOR_POLICY_SIGN_OFF",
                "source_evaluation_hash": record["evaluation_hash"],
            },
            headers={"Idempotency-Key": "api-policy-signoff-missing-requirements"},
        )
        assert blocked.status_code == 422
        assert blocked.json()["detail"] == "POLICY_EVALUATION_SIGN_OFF_REQUIREMENTS_OPEN"

        signed = client.post(
            f"/advisory/policy-evaluations/{evaluation_id}/sign-off-decisions",
            json={
                "actor_id": "policy_checker_1",
                "decision": "APPROVE_FOR_POLICY_SIGN_OFF",
                "source_evaluation_hash": record["evaluation_hash"],
                "resolved_approval_dependencies": record["approval_dependencies"],
                "satisfied_disclosure_requirements": record["disclosure_requirements"],
                "satisfied_consent_requirements": record["consent_requirements"],
                "reason": {"purpose": "requirements reviewed"},
            },
            headers={"Idempotency-Key": "api-policy-signoff-approved"},
        )
        assert signed.status_code == 200
        signed_body = signed.json()
        assert signed_body["workflow"]["sign_off_status"] == "SIGNED_OFF"
        assert signed_body["workflow"]["sign_off_blockers"] == []
        assert signed_body["sign_off_event"]["event_type"] == (
            "POLICY_EVALUATION_SIGN_OFF_RECORDED"
        )
        assert signed_body["replay_metadata"]["report_render_archive_realization"] == (
            "SUPPORTED_BY_RFC0025_SLICE10_SIGNED_OFF_PACKAGE_HANDOFF"
        )


def test_policy_report_package_records_report_render_archive_refs_after_sign_off() -> None:
    captured_requests: list[dict] = []

    def _fake_report_package(*, request: dict) -> dict:
        captured_requests.append(request)
        return {
            "proposal": request["proposal"],
            "report_request_id": request["report_request_id"],
            "report_type": "PORTFOLIO_REVIEW",
            "report_service": "lotus-report",
            "status": "ARCHIVED",
            "generated_at": "2026-05-26T04:00:00Z",
            "report_reference_id": "rjob_policy_001",
            "artifact_url": "/reports/jobs/rjob_policy_001",
            "explanation": {
                "render": {"render_job_id": "rdr_policy_001"},
                "archive": {
                    "archive_request_id": "arch_policy_001",
                    "document_id": "doc_policy_001",
                    "retention_posture": "OWNED_BY_LOTUS_ARCHIVE",
                    "legal_hold_posture": "OWNED_BY_LOTUS_ARCHIVE",
                    "access_audit_ref": "audit_policy_001",
                },
            },
        }

    api_main.request_policy_sign_off_report_package_with_lotus_report = _fake_report_package

    with TestClient(app) as client:
        _activate_sg_pack(client)
        created = client.post(
            "/advisory/proposals/pp_policy_report_001/versions/ppv_policy_report_001/policy-evaluations",
            json=_sg_pending_payload(),
            headers={"Idempotency-Key": "api-policy-eval-report-001"},
        )
        assert created.status_code == 200
        record = created.json()["record"]
        evaluation_id = record["evaluation_id"]

        unsigned = client.post(
            f"/advisory/policy-evaluations/{evaluation_id}/report-packages",
            json={
                "requested_by": "policy_checker_1",
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "source_evaluation_hash": record["evaluation_hash"],
                "requested_output_formats": ["pdf"],
            },
            headers={"Idempotency-Key": "api-policy-report-unsigned"},
        )
        assert unsigned.status_code == 422
        assert unsigned.json()["detail"] == "POLICY_REPORT_PACKAGE_REQUIRES_SIGN_OFF"

        signed = client.post(
            f"/advisory/policy-evaluations/{evaluation_id}/sign-off-decisions",
            json={
                "actor_id": "policy_checker_1",
                "decision": "APPROVE_FOR_POLICY_SIGN_OFF",
                "source_evaluation_hash": record["evaluation_hash"],
                "resolved_approval_dependencies": record["approval_dependencies"],
                "satisfied_disclosure_requirements": record["disclosure_requirements"],
                "satisfied_consent_requirements": record["consent_requirements"],
                "reason": {"purpose": "requirements reviewed"},
            },
            headers={"Idempotency-Key": "api-policy-report-signoff"},
        )
        assert signed.status_code == 200

        report = client.post(
            f"/advisory/policy-evaluations/{evaluation_id}/report-packages",
            json={
                "requested_by": "policy_checker_1",
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "source_evaluation_hash": record["evaluation_hash"],
                "requested_output_formats": ["pdf"],
                "reason": {"purpose": "policy sign-off package"},
            },
            headers={"Idempotency-Key": "api-policy-report-package"},
        )
        assert report.status_code == 200
        body = report.json()
        assert body["report_package_event"]["event_type"] == (
            "POLICY_EVALUATION_REPORT_ARCHIVE_RECORDED"
        )
        assert body["report_package_event"]["reason_json"]["report_package_id"] == (
            "rjob_policy_001"
        )
        assert body["report_package_event"]["reason_json"]["render"]["render_job_id"] == (
            "rdr_policy_001"
        )
        assert body["report_package_event"]["reason_json"]["archive"]["document_id"] == (
            "doc_policy_001"
        )
        assert body["report"]["explanation"]["archive"]["access_audit_ref"] == ("audit_policy_001")
        assert captured_requests[0]["policy_sign_off_package"]["client_ready_publication"] == (
            "BLOCKED"
        )
        assert captured_requests[0]["policy_sign_off_package"]["workflow"]["sign_off_status"] == (
            "SIGNED_OFF"
        )

        replayed = client.post(
            f"/advisory/policy-evaluations/{evaluation_id}/report-packages",
            json={
                "requested_by": "policy_checker_1",
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "source_evaluation_hash": record["evaluation_hash"],
                "requested_output_formats": ["pdf"],
                "reason": {"purpose": "policy sign-off package"},
            },
            headers={"Idempotency-Key": "api-policy-report-package"},
        )
        assert replayed.status_code == 200
        assert replayed.json()["replayed"] is True
        assert len(captured_requests) == 1

        lineage = client.get(f"/advisory/policy-evaluations/{evaluation_id}/lineage")
        assert lineage.status_code == 200
        event_types = [event["event_type"] for event in lineage.json()["audit_events"]]
        assert event_types[-1] == "POLICY_EVALUATION_REPORT_ARCHIVE_RECORDED"


def test_policy_report_package_blocks_client_ready_document_request() -> None:
    with TestClient(app) as client:
        _activate_sg_pack(client)
        created = client.post(
            "/advisory/proposals/pp_policy_report_blocked/versions/ppv_policy_report_blocked/policy-evaluations",
            json=_sg_pending_payload(),
            headers={"Idempotency-Key": "api-policy-eval-report-blocked"},
        )
        assert created.status_code == 200
        record = created.json()["record"]

        blocked = client.post(
            f"/advisory/policy-evaluations/{record['evaluation_id']}/report-packages",
            json={
                "requested_by": "policy_checker_1",
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "source_evaluation_hash": record["evaluation_hash"],
                "requested_output_formats": ["pdf"],
                "client_ready_document_requested": True,
            },
            headers={"Idempotency-Key": "api-policy-report-client-ready-blocked"},
        )
        assert blocked.status_code == 422
        assert blocked.json()["detail"] == "POLICY_CLIENT_READY_DOCUMENT_NOT_SUPPORTED"


def test_policy_ai_evidence_records_bounded_lineage_without_mutating_policy(
    monkeypatch,
) -> None:
    captured_requests: list[dict] = []

    def _fake_policy_ai_evidence(**kwargs) -> PolicyAiEvidenceDraft:
        captured_requests.append(kwargs)
        return PolicyAiEvidenceDraft(
            status="REVIEW_REQUIRED",
            sections=(
                {
                    "section_key": "POLICY_POSTURE",
                    "title": "Policy Posture",
                    "text": "Policy evidence summary for compliance review.",
                    "review_state": "REVIEW_REQUIRED",
                },
            ),
            lineage={
                "workflow_pack_id": "policy_evidence_summary.pack",
                "workflow_pack_version": "v1",
                "workflow_run_id": "packrun_policy_ai_001",
                "fallback_reason": None,
            },
            review_guidance=("Review against immutable policy evaluation hash.",),
        )

    monkeypatch.setattr(
        policy_ai,
        "generate_policy_evidence_summary_with_lotus_ai",
        _fake_policy_ai_evidence,
    )

    with TestClient(app) as client:
        _activate_sg_pack(client)
        created = client.post(
            "/advisory/proposals/pp_policy_ai_001/versions/ppv_policy_ai_001/policy-evaluations",
            json=_sg_pending_payload(),
            headers={"Idempotency-Key": "api-policy-eval-ai-001"},
        )
        assert created.status_code == 200
        record = created.json()["record"]
        original_status = record["evaluation_status"]

        response = client.post(
            f"/advisory/policy-evaluations/{record['evaluation_id']}/ai-evidence",
            json={
                "requested_by": "policy_checker_1",
                "source_evaluation_hash": record["evaluation_hash"],
                "requested_actions": ["SUMMARIZE_POLICY_POSTURE"],
                "reason": {"purpose": "policy evidence explanation"},
            },
            headers={"Idempotency-Key": "api-policy-ai-evidence-001"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["replayed"] is False
        assert body["ai_event"]["event_type"] == "POLICY_EVALUATION_AI_EVIDENCE_RECORDED"
        assert body["policy_evidence"]["status"] == "REVIEW_REQUIRED"
        assert body["policy_evidence"]["human_review_required"] is True
        assert body["policy_evidence"]["authoritative_for_policy_status"] is False
        assert body["policy_evidence"]["client_ready_publication"] == "BLOCKED"
        assert body["evaluation"]["evaluation_status"] == original_status
        assert (
            captured_requests[0]["policy_evidence"]["evaluation_hash"]
            == (record["evaluation_hash"])
        )
        assert (
            captured_requests[0]["policy_evidence"]["redaction_profile"][
                "raw_source_evidence_included"
            ]
            is False
        )
        assert "evidence_bundle" not in captured_requests[0]["policy_evidence"]

        replayed = client.post(
            f"/advisory/policy-evaluations/{record['evaluation_id']}/ai-evidence",
            json={
                "requested_by": "policy_checker_1",
                "source_evaluation_hash": record["evaluation_hash"],
                "requested_actions": ["SUMMARIZE_POLICY_POSTURE"],
                "reason": {"purpose": "policy evidence explanation"},
            },
            headers={"Idempotency-Key": "api-policy-ai-evidence-001"},
        )
        assert replayed.status_code == 200
        assert replayed.json()["replayed"] is True
        assert len(captured_requests) == 1

        lineage = client.get(f"/advisory/policy-evaluations/{record['evaluation_id']}/lineage")
        assert lineage.status_code == 200
        assert lineage.json()["audit_events"][-1]["event_type"] == (
            "POLICY_EVALUATION_AI_EVIDENCE_RECORDED"
        )


def test_policy_ai_evidence_rejects_forbidden_action_and_stale_hash() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/advisory/proposals/pp_policy_ai_blocked/versions/ppv_policy_ai_blocked/policy-evaluations",
            json=_create_payload(),
            headers={"Idempotency-Key": "api-policy-eval-ai-blocked"},
        )
        assert created.status_code == 200
        record = created.json()["record"]

        forbidden = client.post(
            f"/advisory/policy-evaluations/{record['evaluation_id']}/ai-evidence",
            json={
                "requested_by": "policy_checker_1",
                "source_evaluation_hash": record["evaluation_hash"],
                "requested_actions": ["APPROVE_POLICY"],
            },
        )
        assert forbidden.status_code == 422
        assert forbidden.json()["detail"] == "POLICY_AI_EVIDENCE_FORBIDDEN_ACTION"

        stale = client.post(
            f"/advisory/policy-evaluations/{record['evaluation_id']}/ai-evidence",
            json={
                "requested_by": "policy_checker_1",
                "source_evaluation_hash": "sha256:stale",
                "requested_actions": ["SUMMARIZE_POLICY_POSTURE"],
            },
        )
        assert stale.status_code == 422
        assert stale.json()["detail"] == "POLICY_AI_EVIDENCE_HASH_MISMATCH"


def test_policy_ai_evidence_records_deterministic_unavailable_posture() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/advisory/proposals/pp_policy_ai_unavailable/versions/ppv_policy_ai_unavailable/policy-evaluations",
            json=_create_payload(),
            headers={"Idempotency-Key": "api-policy-eval-ai-unavailable"},
        )
        assert created.status_code == 200
        record = created.json()["record"]

        response = client.post(
            f"/advisory/policy-evaluations/{record['evaluation_id']}/ai-evidence",
            json={
                "requested_by": "policy_checker_1",
                "source_evaluation_hash": record["evaluation_hash"],
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["policy_evidence"]["status"] == "UNAVAILABLE"
        assert body["policy_evidence"]["lineage"]["fallback_reason"] == (
            "LOTUS_AI_POLICY_EVIDENCE_UNAVAILABLE"
        )
        assert body["policy_evidence"]["sections"] == []
        assert body["evaluation"]["evaluation_hash"] == record["evaluation_hash"]


def test_policy_review_queue_filters_records_that_need_policy_review() -> None:
    with TestClient(app) as client:
        _activate_sg_pack(client)
        created = client.post(
            "/advisory/proposals/pp_policy_queue_001/versions/ppv_policy_queue_001/policy-evaluations",
            json=_sg_pending_payload(),
            headers={"Idempotency-Key": "api-policy-eval-queue-001"},
        )
        assert created.status_code == 200
        evaluation_id = created.json()["record"]["evaluation_id"]
        assert created.json()["record"]["portfolio_id"] == "PB_SG_GLOBAL_BAL_001"

        other_portfolio_payload = _sg_pending_payload()
        other_portfolio_payload["evidence_bundle"]["inputs"]["portfolio_snapshot"][
            "portfolio_id"
        ] = "PB_SG_OTHER_BAL_001"
        other_created = client.post(
            "/advisory/proposals/pp_policy_queue_002/versions/ppv_policy_queue_002/policy-evaluations",
            json=other_portfolio_payload,
            headers={"Idempotency-Key": "api-policy-eval-queue-002"},
        )
        assert other_created.status_code == 200
        other_evaluation_id = other_created.json()["record"]["evaluation_id"]

        queue = client.get("/advisory/policy-evaluations/review-queue")
        assert queue.status_code == 200
        queue_body = queue.json()
        assert [item["evaluation_id"] for item in queue_body["items"]] == [
            evaluation_id,
            other_evaluation_id,
        ]
        assert queue_body["items"][0]["evaluation_status"] == "PENDING_REVIEW"
        assert queue_body["queue_posture"]["workbench_supported"] is True
        assert queue_body["queue_posture"]["workbench_support"] == (
            "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_ONLY_UI"
        )
        assert queue_body["queue_posture"]["client_ready_publication"] == "BLOCKED"

        portfolio_queue = client.get(
            "/advisory/policy-evaluations/review-queue",
            params={
                "evaluation_status": "PENDING_REVIEW",
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            },
        )
        assert portfolio_queue.status_code == 200
        assert [item["evaluation_id"] for item in portfolio_queue.json()["items"]] == [
            evaluation_id
        ]

        ready_queue = client.get(
            "/advisory/policy-evaluations/review-queue",
            params={"evaluation_status": "READY"},
        )
        assert ready_queue.status_code == 200
        assert ready_queue.json()["items"] == []


def test_policy_evaluation_openapi_registers_certified_advise_routes() -> None:
    app.openapi_schema = None
    openapi = app.openapi()
    paths = openapi["paths"]

    create_path = (
        "/advisory/proposals/{proposal_id}/versions/{proposal_version_id}/policy-evaluations"
    )
    assert paths[create_path]["post"]["tags"] == ["Advisory Policy Evaluation"]
    assert (
        paths[create_path]["post"]["parameters"][2]["description"]
        == "Required idempotency key for replay-safe policy evaluation finalization."
    )
    assert "/advisory/policy-evaluations/review-queue" in paths
    assert "/advisory/policy-evaluations/{evaluation_id}/events" in paths
    assert "/advisory/policy-evaluations/{evaluation_id}/lineage" in paths
    assert "/advisory/policy-evaluations/{evaluation_id}/sign-off-package" in paths
    assert "/advisory/policy-evaluations/{evaluation_id}/workflow" in paths
    assert "/advisory/policy-evaluations/{evaluation_id}/sign-off-decisions" in paths
    assert "/advisory/policy-evaluations/{evaluation_id}/report-packages" in paths
    assert "/advisory/policy-evaluations/{evaluation_id}/ai-evidence" in paths
