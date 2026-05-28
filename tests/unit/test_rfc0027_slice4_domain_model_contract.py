from __future__ import annotations

from pathlib import Path

RFC27_PATH = Path("docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md")
SLICE4_PATH = Path("docs/rfcs/RFC-0027-slice-4-domain-model-vocabulary-review-state.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0027_slice4_evidence_is_indexed_and_non_promoting() -> None:
    source_ref = "docs/rfcs/RFC-0027-slice-4-domain-model-vocabulary-review-state.md"

    assert source_ref in _read(RFC27_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)

    slice4 = _read(SLICE4_PATH)
    flat_supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    assert "IMPLEMENTED - PURE DOMAIN CONTRACT ONLY" in slice4
    assert "does not build evidence packets from live sources" in slice4
    assert "Those remain mandatory subsequent RFC-0027 slices" in slice4
    assert "Implemented for governed internal advisor/reviewer copilot interactions" in (
        flat_supported
    )
    assert "active `AdvisoryCopilotInteractionRecord:v1` data-product posture" in flat_supported
    assert "Evidence packets and review events remain audit records" in flat_supported


def test_rfc0027_slice4_records_packet_review_unsupported_and_retention_vocabulary() -> None:
    flat_slice4 = _flat(SLICE4_PATH)

    model_markers = (
        "CopilotEvidencePacket",
        "CopilotEvidencePacketSection",
        "CopilotSourceRef",
        "CopilotLineageRef",
        "CopilotUnsupportedEvidence",
        "CopilotUnsupportedEvidenceReason",
        "CopilotRetentionClass",
        "client_ready_publication = BLOCKED",
    )
    for marker in model_markers:
        assert marker in flat_slice4

    review_markers = (
        "APPROVE_FOR_INTERNAL_USE",
        "APPROVED_FOR_INTERNAL_USE",
        "REJECT",
        "REJECTED",
        "SUPERSEDE",
        "SUPERSEDED",
        "EXPIRE",
        "EXPIRED",
    )
    for marker in review_markers:
        assert marker in flat_slice4

    unsupported_reasons = (
        "SOURCE_NOT_IMPLEMENTED",
        "SOURCE_NOT_AVAILABLE",
        "RESTRICTED_BY_ROLE",
        "QUESTION_OUT_OF_SCOPE",
        "CLIENT_READY_PUBLICATION_BLOCKED",
        "POLICY_APPROVAL_NOT_AVAILABLE",
        "AI_UNAVAILABLE",
    )
    for reason in unsupported_reasons:
        assert reason in flat_slice4


def test_rfc0027_slice4_records_review_boundary_without_client_ready_or_oms_claims() -> None:
    flat_slice4 = _flat(SLICE4_PATH)

    boundaries = (
        "No review action can approve policy findings",
        "approve client-ready publication",
        "send external client communication",
        "create CRM tasks",
        "initiate OMS order lifecycle activity",
        "must not expose raw prompts, provider details, trace IDs, correlation IDs",
    )
    for boundary in boundaries:
        assert boundary in flat_slice4

    assert "test_copilot_evidence_packet_shape_preserves_review_and_lineage_boundaries" in (
        flat_slice4
    )
