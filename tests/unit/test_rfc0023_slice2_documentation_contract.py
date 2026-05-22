from __future__ import annotations

from pathlib import Path

RFC_PATH = Path(
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)
SLICE2_PATH = Path("docs/rfcs/RFC-0023-slice-2-cleanup-and-structure.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0023_slice2_cleanup_and_structure_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice2_text = SLICE2_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0023-slice-2-cleanup-and-structure.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Boundary Decisions",
        "## Cleanup Performed",
        "## Retained With Rationale",
        "## Acceptance Evidence",
        "## README And Wiki Decision",
    ):
        assert section in slice2_text

    assert "IMPLEMENTED - CLEANUP AND STRUCTURE ONLY" in slice2_text
    assert "does not implement generated proposal narrative" in slice2_text
    assert "workspace-rationale evidence construction" in slice2_text


def test_rfc0023_slice2_supported_features_remains_non_claiming() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "Slices 0-2 complete" in supported_features
    assert "generated proposal narrative remains planned" in supported_features
    assert "Proposal narrative | Supported" not in supported_features
    assert "Client-ready proposal commentary | Supported" not in supported_features
