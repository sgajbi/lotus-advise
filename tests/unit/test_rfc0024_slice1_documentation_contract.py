from __future__ import annotations

from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
SLICE1_PATH = Path("docs/rfcs/RFC-0024-slice-1-platform-automation-and-scaffolding-review.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0024_slice1_records_platform_scaffolding_decision() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice1_text = SLICE1_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0024-slice-1-platform-automation-and-scaffolding-review.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    required_sections = (
        "## Reviewed Automation And Scaffolding",
        "## Rejected One-Off Local Scaffolding",
        "## Required Controls For Later RFC-0024 Slices",
        "## No Platform Change Rationale",
        "## Acceptance Evidence",
        "## Wiki And README Decision",
    )
    for section in required_sections:
        assert section in slice1_text

    assert "IMPLEMENTED - REVIEWED; NO PLATFORM CHANGE REQUIRED" in slice1_text
    assert "No `lotus-platform` code or automation change is required" in slice1_text
    assert "RFC-0024 may proceed to Slice 2 cleanup and structure" in slice1_text


def test_rfc0024_slice1_rejects_one_off_scaffolding_and_pins_memo_controls() -> None:
    slice1_text = SLICE1_PATH.read_text(encoding="utf-8")

    for rejected_scope in (
        "a `lotus-advise`-only memo certification CLI",
        "a local proof-pack schema that duplicates platform evidence",
        "a local trust telemetry substitute",
        "local wiki publication scripts outside `Sync-RepoWikis.ps1`",
    ):
        assert rejected_scope in slice1_text

    for later_control in (
        "Memo domain model and builder",
        "Memo persistence, replay, and idempotency",
        "Memo data-product promotion",
        "Gateway and Workbench realization",
    ):
        assert later_control in slice1_text


def test_rfc0024_slice1_keeps_supported_features_non_claiming() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "Slices 0-2 are complete as non-claiming source-map" in supported_features
    assert "Existing platform/repo-native controls are sufficient" in supported_features
    assert "Memo generation, memo APIs, memo persistence" in supported_features
    assert "client-ready memo claims remain planned" in supported_features
    assert "Advisor proposal memo | Supported" not in supported_features
    assert "Client-ready memo publication | Supported" not in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1 | Supported" not in supported_features
