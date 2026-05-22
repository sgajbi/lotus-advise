from __future__ import annotations

from pathlib import Path

RFC_PATH = Path(
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)
SLICE1_PATH = Path("docs/rfcs/RFC-0023-slice-1-platform-automation-and-scaffolding-review.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0023_slice1_records_platform_scaffolding_decision() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice1_text = SLICE1_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0023-slice-1-platform-automation-and-scaffolding-review.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Reviewed Automation And Scaffolding",
        "## Rejected One-Off Local Scaffolding",
        "## Required Controls For Later RFC-0023 Slices",
        "## No Platform Change Rationale",
        "## Acceptance Evidence",
        "## Wiki And README Decision",
    ):
        assert section in slice1_text

    assert "IMPLEMENTED - REVIEWED; NO PLATFORM CHANGE REQUIRED" in slice1_text
    assert "No `lotus-platform` code or automation change is required" in slice1_text
    assert "RFC-0023 may proceed to Slice 2 cleanup and structure" in slice1_text


def test_rfc0023_slice1_keeps_supported_features_non_claiming() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "source authority, platform-scaffolding review, cleanup/structure" in (
        supported_features
    )
    assert "contract baseline" in supported_features
    assert "deterministic advisor-review artifact-path narrative" in supported_features
    assert "AI-assisted, persisted/replayable" in supported_features
    assert "Proposal narrative | Supported" not in supported_features
    assert "Client-ready proposal commentary | Supported" not in supported_features
