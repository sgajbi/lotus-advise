from __future__ import annotations

from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
SLICE2_PATH = Path("docs/rfcs/RFC-0024-slice-2-cleanup-and-structure.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_ARCHITECTURE_PATH = Path("wiki/Architecture.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0024_slice2_cleanup_evidence_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice2_text = SLICE2_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0024-slice-2-cleanup-and-structure.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    required_sections = (
        "## Structural Change",
        "## Removed Or Avoided Complexity",
        "## Dedicated Boundary Direction For Later Memo Work",
        "## Acceptance Evidence",
        "## Wiki And README Decision",
    )
    for section in required_sections:
        assert section in slice2_text

    assert "IMPLEMENTED - CLEANUP ONLY; NO MEMO SUPPORT PROMOTED" in slice2_text
    assert "Removed `src/api/services/proposal_report_narrative.py`" in slice2_text
    assert "RFC-0024 may proceed to Slice 3 data-product" in slice2_text


def test_rfc0024_slice2_pins_core_report_handoff_boundary() -> None:
    slice2_text = SLICE2_PATH.read_text(encoding="utf-8")
    architecture_text = WIKI_ARCHITECTURE_PATH.read_text(encoding="utf-8")

    assert "`src/core/proposals/report_narrative_package.py`" in slice2_text
    assert "review-state, hash-continuity, source-lineage" in slice2_text
    assert "`src/core/proposals/report_narrative_package.py`" in architecture_text
    assert "out of API services before RFC-0024 memo report packages" in architecture_text


def test_rfc0024_slice2_keeps_supported_features_non_claiming() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "Slices 0-4 are complete as non-claiming source-map" in supported_features
    assert "cleanup/structure" in supported_features
    assert "reviewed narrative report-package business rules now live" in supported_features
    assert "Slice 7 is complete for canonical `lotus-advise` memo" in supported_features
    assert "`AdvisoryProposalMemoEvidencePack:v1` remains unpromoted" in supported_features
    assert "Gateway, Workbench, report/render/archive realization" in supported_features
    assert "client-ready memo claims remain planned" in supported_features
    assert "Advisor proposal memo | Supported" not in supported_features
    assert "Client-ready memo publication | Supported" not in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1 | Supported" not in supported_features
