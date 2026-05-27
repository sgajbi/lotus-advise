from __future__ import annotations

from pathlib import Path

RFC27_PATH = Path("docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md")
SLICE5_PATH = Path("docs/rfcs/RFC-0027-slice-5-evidence-packet-redaction-projection.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0027_slice5_evidence_is_indexed_and_non_promoting() -> None:
    source_ref = "docs/rfcs/RFC-0027-slice-5-evidence-packet-redaction-projection.md"

    assert source_ref in _read(RFC27_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)

    slice5 = _read(SLICE5_PATH)
    flat_supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    assert "IMPLEMENTED - PURE EVIDENCE-PACKET BUILDER ONLY" in slice5
    assert "does not read live proposal, memo, policy, cockpit, report, or operations sources" in (
        slice5
    )
    assert "Those remain mandatory subsequent RFC-0027 slices" in slice5
    assert "Slice 5 adds pure evidence-packet projection without runtime support promotion" in (
        flat_supported
    )
    assert "before any supported copilot claim is promoted" in flat_supported


def test_rfc0027_slice5_records_projection_hash_and_redaction_behavior() -> None:
    flat_slice5 = _flat(SLICE5_PATH)

    behaviors = (
        "orders sections by the required action-family evidence map",
        "includes only sections allowed for the requested audience",
        "RESTRICTED_BY_ROLE",
        "SOURCE_NOT_AVAILABLE",
        "preserves source refs and content hashes",
        "adds a packet lineage ref owned by `lotus-advise`",
        "computes a deterministic `sha256:` evidence-packet hash",
        "rejects business-copy leakage of raw prompt, provider response, trace ID",
        "keeps `client_ready_publication` blocked",
    )
    for behavior in behaviors:
        assert behavior in flat_slice5


def test_rfc0027_slice5_records_tests_and_no_day2_deferral() -> None:
    flat_slice5 = _flat(SLICE5_PATH)

    tests = (
        "test_copilot_evidence_packet_builder_projects_allowed_sections_and_hashes",
        "test_copilot_evidence_packet_builder_restricts_sections_by_audience",
        "test_copilot_evidence_packet_builder_rejects_technical_copy_leakage",
    )
    for test_name in tests:
        assert test_name in flat_slice5

    assert "This is not day-2 or wave-2 deferral" in flat_slice5
    assert "Slice 6 guardrail and unsupported-evidence engine" in flat_slice5
