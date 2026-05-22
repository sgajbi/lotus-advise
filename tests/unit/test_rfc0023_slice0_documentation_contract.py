from __future__ import annotations

from pathlib import Path

RFC_PATH = Path(
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)
SLICE0_PATH = Path(
    "docs/rfcs/RFC-0023-slice-0-critical-review-source-map-and-product-gap-allocation.md"
)
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0023_slice0_source_map_is_indexed_without_promoting_capability() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice0_text = SLICE0_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_map_ref = (
        "docs/rfcs/RFC-0023-slice-0-critical-review-source-map-and-product-gap-allocation.md"
    )
    assert source_map_ref in rfc_text
    assert source_map_ref in index_text
    assert source_map_ref in wiki_index_text

    required_sections = (
        "## Source Authority Matrix",
        "## Product-Gap Allocation",
        "## Cross-Repository Source Map",
        "## No WTBD Execution Decision",
        "## Documentation and Feature-Truth Guard",
    )
    for section in required_sections:
        assert section in slice0_text

    assert "IMPLEMENTED - SOURCE-MAP AND SCOPE-GATE ONLY" in slice0_text
    assert "does not implement proposal narrative generation" in slice0_text


def test_supported_features_keep_rfc0023_current_state_conservative() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "Workspace AI rationale | Supported through governed seam" in supported_features
    assert "RFC-0023" in supported_features
    assert (
        "Slice 0 source-map and product-gap allocation complete; generated proposal narrative "
        "remains planned"
    ) in supported_features
    assert "generated proposal narrative, client-ready commentary, and" in supported_features
    assert "document artifact inclusion remain planned" in supported_features
    assert "Proposal narrative | Supported" not in supported_features
    assert "Client-ready proposal commentary | Supported" not in supported_features
