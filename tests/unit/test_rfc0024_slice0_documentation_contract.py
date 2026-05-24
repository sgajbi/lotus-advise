from __future__ import annotations

from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
SLICE0_PATH = Path(
    "docs/rfcs/RFC-0024-slice-0-critical-review-source-map-and-product-gap-allocation.md"
)
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0024_slice0_source_map_is_indexed_without_promoting_memo_support() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice0_text = SLICE0_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = (
        "docs/rfcs/RFC-0024-slice-0-critical-review-source-map-and-product-gap-allocation.md"
    )
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    required_sections = (
        "## Source Authority Matrix",
        "## Product-Gap Allocation",
        "## Cross-Repository Source Map",
        "## First Supported Memo Scope",
        "## No WTBD Execution Decision",
        "## Documentation and Feature-Truth Guard",
    )
    for section in required_sections:
        assert section in slice0_text

    assert "IMPLEMENTED - SOURCE-MAP AND SCOPE-GATE ONLY" in slice0_text
    assert "does not implement advisor proposal memo generation" in slice0_text


def test_supported_features_keep_rfc0024_current_state_non_claiming() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "`RFC-0024`" in supported_features
    assert "Slices 0-4 are complete as non-claiming source-map" in supported_features
    assert "product-gap allocation" in supported_features
    assert "Slice 7 is complete for canonical `lotus-advise` memo" in supported_features
    assert "`AdvisoryProposalMemoEvidencePack:v1` remains unpromoted" in supported_features
    assert "Gateway, Workbench, report/render/archive realization" in supported_features
    assert "client-ready memo claims remain planned" in supported_features
    assert "Advisor proposal memo | Supported" not in supported_features
    assert "Client-ready memo publication | Supported" not in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1 | Supported" not in supported_features


def test_rfc0024_slice0_resolves_source_gaps_as_blocked_not_positive_claims() -> None:
    slice0_text = SLICE0_PATH.read_text(encoding="utf-8")

    assert "Positive client-ready wording is forbidden until source-backed evidence exists" in (
        slice0_text
    )
    assert "missing source facts as `PENDING_REVIEW` or `BLOCKED`" in slice0_text
    assert "Existing reviewed narrative and report/render/archive support is not memo support" in (
        slice0_text
    )
