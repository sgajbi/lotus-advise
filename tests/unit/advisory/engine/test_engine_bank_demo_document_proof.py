from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.bank_demo_proof import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
    AdvisoryDocumentProof,
    AdvisoryDocumentProofSummary,
    build_document_proof_summary,
)
from tests.unit.advisory.engine.test_engine_bank_demo_proof_capture import _live_runtime_payload


def test_document_proof_summary_preserves_report_render_archive_posture() -> None:
    summary = build_document_proof_summary(_live_runtime_payload())

    assert summary.contract_name == "AdvisoryDocumentProofSummary"
    assert summary.client_ready_publication == "BLOCKED"
    assert {document.document_family for document in summary.documents} == {
        "PROPOSAL_MEMO",
        "POLICY_SIGN_OFF",
    }
    for document in summary.documents:
        assert document.report_package_status == "ARCHIVED"
        assert document.requested_output_formats == ["pdf"]
        assert document.render_ref_status == "RECORDED"
        assert document.archive_ref_status == "RECORDED"
        assert document.archive_retention_posture == "OWNED_BY_LOTUS_ARCHIVE"
        assert document.archive_legal_hold_posture == "OWNED_BY_LOTUS_ARCHIVE"
        assert document.archive_access_audit_ref_status == "RECORDED"
        assert document.claim_posture == "CLIENT_READY_BLOCKED"
        assert "NOT_SUPPORTED" in document.client_ready_document_status


def test_document_proof_blocks_archived_packages_without_archive_controls() -> None:
    with pytest.raises(ValidationError, match="recorded render/archive refs"):
        AdvisoryDocumentProof(
            document_family="PROPOSAL_MEMO",
            claim_posture="CLIENT_READY_BLOCKED",
            report_status="READY",
            report_package_status="ARCHIVED",
            requested_output_formats=["pdf"],
            render_ref_status="RECORDED",
            archive_ref_status="NOT_RETURNED",
            archive_retention_posture="OWNED_BY_LOTUS_ARCHIVE",
            archive_legal_hold_posture="OWNED_BY_LOTUS_ARCHIVE",
            archive_access_audit_ref_status="RECORDED",
            client_ready_document_status="MEMO_CLIENT_READY_DOCUMENT_NOT_SUPPORTED",
        )

    with pytest.raises(ValidationError, match="NOT_SUPPORTED document status"):
        AdvisoryDocumentProof(
            document_family="POLICY_SIGN_OFF",
            claim_posture="CLIENT_READY_BLOCKED",
            report_status="READY",
            report_package_status="BLOCKED",
            requested_output_formats=["pdf"],
            render_ref_status="NOT_RETURNED",
            archive_ref_status="NOT_RETURNED",
            archive_retention_posture="NOT_RETURNED",
            archive_legal_hold_posture="NOT_RETURNED",
            archive_access_audit_ref_status="NOT_RETURNED",
            client_ready_document_status="APPROVED",
        )


def test_document_proof_rejects_unsafe_output_formats_and_degraded_reasons() -> None:
    with pytest.raises(ValidationError, match="requested output format is not supported"):
        AdvisoryDocumentProof(
            document_family="PROPOSAL_MEMO",
            claim_posture="CLIENT_READY_BLOCKED",
            report_status="READY",
            report_package_status="ARCHIVED",
            requested_output_formats=["pdf?token=should-not-leak"],
            render_ref_status="RECORDED",
            archive_ref_status="RECORDED",
            archive_retention_posture="OWNED_BY_LOTUS_ARCHIVE",
            archive_legal_hold_posture="OWNED_BY_LOTUS_ARCHIVE",
            archive_access_audit_ref_status="RECORDED",
            client_ready_document_status="MEMO_CLIENT_READY_DOCUMENT_NOT_SUPPORTED",
        )

    with pytest.raises(ValidationError, match="sensitive technical detail"):
        AdvisoryDocumentProof(
            document_family="PROPOSAL_MEMO",
            claim_posture="CLIENT_READY_BLOCKED",
            report_status="READY",
            report_package_status="BLOCKED",
            requested_output_formats=["pdf"],
            render_ref_status="NOT_RETURNED",
            archive_ref_status="NOT_RETURNED",
            archive_retention_posture="NOT_RETURNED",
            archive_legal_hold_posture="NOT_RETURNED",
            archive_access_audit_ref_status="NOT_RETURNED",
            client_ready_document_status="MEMO_CLIENT_READY_DOCUMENT_NOT_SUPPORTED",
            degraded_reason="Raw prompt material was not available.",
        )


def test_document_proof_summary_rejects_duplicate_document_families() -> None:
    document = AdvisoryDocumentProof(
        document_family="PROPOSAL_MEMO",
        claim_posture="CLIENT_READY_BLOCKED",
        report_status="READY",
        report_package_status="ARCHIVED",
        requested_output_formats=["pdf"],
        render_ref_status="RECORDED",
        archive_ref_status="RECORDED",
        archive_retention_posture="OWNED_BY_LOTUS_ARCHIVE",
        archive_legal_hold_posture="OWNED_BY_LOTUS_ARCHIVE",
        archive_access_audit_ref_status="RECORDED",
        client_ready_document_status="MEMO_CLIENT_READY_DOCUMENT_NOT_SUPPORTED",
    )

    with pytest.raises(ValidationError, match="document proof families must be unique"):
        AdvisoryDocumentProofSummary(
            scenario_id=RFC28_CANONICAL_SCENARIO_ID,
            primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
            proof_marker=RFC28_CANONICAL_PROOF_MARKER,
            documents=[document, document],
        )
