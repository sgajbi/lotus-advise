from __future__ import annotations

from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
SLICE4_PATH = Path("docs/rfcs/RFC-0024-slice-4-upstream-source-evidence-completion.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0024_slice4_source_readiness_evidence_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice4_text = SLICE4_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0024-slice-4-upstream-source-evidence-completion.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    required_sections = (
        "## Source Evidence Boundary",
        "## Implementation",
        "## Acceptance Evidence",
        "## Wiki And README Decision",
    )
    for section in required_sections:
        assert section in slice4_text

    assert "IMPLEMENTED - SOURCE-READINESS ONLY" in slice4_text
    assert "`rfc0024.memo-source-readiness.v1`" in slice4_text
    assert "31-Dec-3999" in slice4_text


def test_rfc0024_slice4_keeps_memo_support_unpromoted() -> None:
    slice4_text = SLICE4_PATH.read_text(encoding="utf-8")
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "No memo routes" in slice4_text
    assert "client-ready memo claims remain planned" in supported_features
    assert "Slices 0-4 are complete" in supported_features
    assert "rfc0024.memo-source-readiness.v1" in supported_features
    assert "Advisor proposal memo | Supported" not in supported_features
    assert "Client-ready memo publication | Supported" not in supported_features
