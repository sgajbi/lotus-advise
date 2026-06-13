from __future__ import annotations

import pytest

from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.exceptions import ProposalValidationError
from src.core.proposals.report_narrative_package import (
    build_reviewed_narrative_report_package,
    summarize_narrative_report_package,
)


def _reviewed_replay_evidence() -> dict:
    narrative = {
        "narrative_id": "pnar_report_001",
        "status": "READY_FOR_ADVISOR_REVIEW",
        "generation_mode": "DETERMINISTIC_TEMPLATE",
        "audience": "ADVISOR_REVIEW",
        "policy_version": "proposal-narrative-policy.v1",
        "sections": [
            {
                "section_key": "EXECUTIVE_SUMMARY",
                "title": "Executive summary",
                "text": "Advisor-reviewed proposal context.",
            },
            {
                "section_id": "MISSING_BODY",
                "title": "Skipped section",
            },
        ],
        "disclosures": [{"disclosure_id": "standard_advisor_review"}],
        "guardrail_results": [{"guardrail": "unsupported_claims", "status": "PASS"}],
        "limitations": [{"limitation_code": "CLIENT_READY_BLOCKED"}],
        "ai_lineage": {"mode": "not_requested"},
    }
    return {
        "proposal_narrative": narrative,
        "proposal_narrative_review": {
            "review_id": "pnrv_report_001",
            "review_state": "APPROVED_FOR_ADVISOR_USE",
            "client_ready_status": "NOT_CLIENT_READY",
            "reviewed_by": "advisor_1",
            "reviewed_at": "2026-05-23T06:00:00Z",
            "source_narrative_hash": hash_canonical_payload(narrative),
        },
        "request_hash": "sha256:request",
        "artifact_hash": "sha256:artifact",
        "simulation_hash": "sha256:simulation",
        "delivery": {
            "execution": {
                "handoff_status": "NOT_REQUESTED",
                "execution_system_of_record": "DOWNSTREAM_EXECUTION_SYSTEM",
            }
        },
    }


def test_build_reviewed_narrative_report_package_keeps_report_handoff_source_backed():
    package = build_reviewed_narrative_report_package(
        proposal_id="pp_report_001",
        version_no=2,
        replay_evidence=_reviewed_replay_evidence(),
    )

    assert package["package_status"] == "INCLUDED_REVIEWED_NARRATIVE"
    assert package["usage"] == "ADVISOR_REVIEW_AND_REPORT_CONTEXT"
    assert package["proposal_id"] == "pp_report_001"
    assert package["proposal_version_no"] == 2
    assert package["review"]["review_state"] == "APPROVED_FOR_ADVISOR_USE"
    assert package["review"]["client_ready_status"] == "NOT_CLIENT_READY"
    assert package["source_lineage"] == {
        "source_narrative_hash": package["review"]["source_narrative_hash"],
        "request_hash": "sha256:request",
        "artifact_hash": "sha256:artifact",
        "simulation_hash": "sha256:simulation",
    }
    assert package["sections"] == [
        {
            "section_id": "EXECUTIVE_SUMMARY",
            "title": "Executive summary",
            "body": "Advisor-reviewed proposal context.",
        }
    ]
    assert package["execution_boundary"]["execution_system_of_record"] == (
        "DOWNSTREAM_EXECUTION_SYSTEM"
    )


def test_report_narrative_sections_prefer_canonical_fields_and_strip_compatibility_keys():
    replay_evidence = _reviewed_replay_evidence()
    replay_evidence["proposal_narrative"]["sections"] = [
        {
            "section_id": "CANONICAL_SECTION",
            "section_key": "LEGACY_SECTION",
            "title": "  Canonical title  ",
            "body": "  Canonical body.  ",
            "text": "Legacy body.",
            "source_ref": "advisor-reviewed-narrative",
        },
        {
            "section_key": "LEGACY_ONLY_SECTION",
            "title": "Legacy title",
            "text": "Legacy body.",
        },
        {
            "section_id": "MISSING_BODY",
            "title": "Skipped section",
        },
        "not-a-section",
    ]
    replay_evidence["proposal_narrative_review"]["source_narrative_hash"] = hash_canonical_payload(
        replay_evidence["proposal_narrative"]
    )

    package = build_reviewed_narrative_report_package(
        proposal_id="pp_report_001",
        version_no=2,
        replay_evidence=replay_evidence,
    )

    assert package["sections"] == [
        {
            "section_id": "CANONICAL_SECTION",
            "title": "Canonical title",
            "body": "Canonical body.",
            "source_ref": "advisor-reviewed-narrative",
        },
        {
            "section_id": "LEGACY_ONLY_SECTION",
            "title": "Legacy title",
            "body": "Legacy body.",
        },
    ]
    assert all(
        "section_key" not in section and "text" not in section for section in package["sections"]
    )


def test_reviewed_narrative_report_package_fails_closed_for_unapproved_review():
    replay_evidence = _reviewed_replay_evidence()
    replay_evidence["proposal_narrative_review"]["review_state"] = "REJECTED"

    with pytest.raises(
        ProposalValidationError,
        match="PROPOSAL_REPORT_NARRATIVE_REVIEW_NOT_APPROVED",
    ):
        build_reviewed_narrative_report_package(
            proposal_id="pp_report_001",
            version_no=2,
            replay_evidence=replay_evidence,
        )


def test_reviewed_narrative_report_package_fails_closed_for_hash_drift():
    replay_evidence = _reviewed_replay_evidence()
    replay_evidence["proposal_narrative"]["sections"][0]["text"] = "Changed after review."

    with pytest.raises(
        ProposalValidationError,
        match="PROPOSAL_REPORT_NARRATIVE_REVIEW_HASH_MISMATCH",
    ):
        build_reviewed_narrative_report_package(
            proposal_id="pp_report_001",
            version_no=2,
            replay_evidence=replay_evidence,
        )


def test_summarize_narrative_report_package_returns_support_safe_lineage_only():
    package = build_reviewed_narrative_report_package(
        proposal_id="pp_report_001",
        version_no=2,
        replay_evidence=_reviewed_replay_evidence(),
    )

    summary = summarize_narrative_report_package(package)

    assert summary == {
        "package_status": "INCLUDED_REVIEWED_NARRATIVE",
        "usage": "ADVISOR_REVIEW_AND_REPORT_CONTEXT",
        "proposal_version_no": 2,
        "narrative_id": "pnar_report_001",
        "review_id": "pnrv_report_001",
        "review_state": "APPROVED_FOR_ADVISOR_USE",
        "client_ready_status": "NOT_CLIENT_READY",
        "source_narrative_hash": package["review"]["source_narrative_hash"],
    }
    assert "sections" not in summary
