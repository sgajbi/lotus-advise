from __future__ import annotations

from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
SLICE3_PATH = Path("docs/rfcs/RFC-0024-slice-3-data-product-and-platform-hardening.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0024_slice3_data_product_evidence_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice3_text = SLICE3_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0024-slice-3-data-product-and-platform-hardening.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    required_sections = (
        "## Data Product Posture",
        "## Trust Telemetry Posture",
        "## Platform Hardening Posture",
        "## Acceptance Evidence",
        "## Wiki And README Decision",
    )
    for section in required_sections:
        assert section in slice3_text

    assert "IMPLEMENTED - PROPOSED/BLOCKED DATA PRODUCT" in slice3_text
    assert "`AdvisoryProposalMemoEvidencePack:v1`" in slice3_text
    assert "Capability promotion is forbidden" in slice3_text


def test_rfc0024_slice3_keeps_memo_capability_unpromoted() -> None:
    slice3_text = SLICE3_PATH.read_text(encoding="utf-8")
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "product has no `current_routes`" in slice3_text
    assert "No memo row is added in this slice" in slice3_text
    assert "active mesh policy" in slice3_text
    assert "Slices 0-4 are complete as non-claiming source-map" in supported_features
    assert "proposed/blocked governance posture" in supported_features
    assert "Slice 7 is complete for canonical `lotus-advise` memo" in supported_features
    assert "`AdvisoryProposalMemoEvidencePack:v1` remains unpromoted" in supported_features
    assert "Gateway, Workbench, report/render/archive realization" in supported_features
    assert "client-ready memo claims remain planned" in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1 | Supported" not in supported_features
