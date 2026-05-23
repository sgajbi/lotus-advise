from __future__ import annotations

from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
SLICE5_PATH = Path("docs/rfcs/RFC-0024-slice-5-memo-domain-model-and-pure-builder.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0024_slice5_memo_builder_evidence_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice5_text = SLICE5_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0024-slice-5-memo-domain-model-and-pure-builder.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    required_sections = (
        "## Implemented Behavior",
        "## Design Review",
        "## Acceptance Review",
        "## Wiki And README Decision",
        "## Remaining Gates",
    )
    for section in required_sections:
        assert section in slice5_text

    assert "`AdvisoryProposalMemoEvidencePack:v1`" in slice5_text
    assert "src/core/proposals/memo_builder.py" in slice5_text
    assert "deterministic pure" in slice5_text


def test_rfc0024_slice5_keeps_product_support_unpromoted() -> None:
    slice5_text = SLICE5_PATH.read_text(encoding="utf-8")
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "No API routes" in slice5_text
    assert "Slices 0-5 are complete" in supported_features
    assert "client-ready memo claims remain planned" in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1` remains unpromoted" in supported_features
    assert "Advisor proposal memo | Supported" not in supported_features
    assert "Client-ready memo publication | Supported" not in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1 | Supported" not in supported_features
