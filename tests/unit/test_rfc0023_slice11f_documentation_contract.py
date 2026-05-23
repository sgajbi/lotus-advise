from __future__ import annotations

from pathlib import Path

RFC_PATH = Path(
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)
SLICE11F_PATH = Path(
    "docs/rfcs/RFC-0023-slice-11F-narrative-data-product-trust-capability-promotion.md"
)
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
WIKI_API_SURFACE_PATH = Path("wiki/API-Surface.md")
WIKI_MESH_PRODUCTS_PATH = Path("wiki/Mesh-Data-Products.md")
REPO_CONTEXT_PATH = Path("REPOSITORY-ENGINEERING-CONTEXT.md")


def test_rfc0023_slice11f_narrative_data_product_promotion_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice11f_text = SLICE11F_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0023-slice-11F-narrative-data-product-trust-capability-promotion.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Purpose",
        "## Implemented Behavior",
        "## Acceptance Review",
        "## Local Validation",
        "## Remaining Gates",
    ):
        assert section in slice11f_text

    assert "ProposalNarrativeEvidence:v1" in slice11f_text
    assert "advisory.proposals.reviewed_narrative_evidence" in slice11f_text
    assert "advisory_proposal_reviewed_narrative_evidence" in slice11f_text


def test_rfc0023_slice11f_supported_features_promote_only_advisor_review_evidence() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "Slice 11F is complete" in supported_features
    assert "ProposalNarrativeEvidence:v1" in supported_features
    assert "trust telemetry" in supported_features
    assert "platform catalog/certification" in supported_features
    assert "advisory.proposals.reviewed_narrative_evidence" in supported_features
    assert "advisory_proposal_reviewed_narrative_evidence" in supported_features
    assert "Client-ready proposal commentary | Supported" not in supported_features
    assert "Gated items still include compliance-review, client-draft, client-ready commentary" in (
        supported_features
    )


def test_rfc0023_slice11f_api_and_mesh_docs_expose_bounded_capability() -> None:
    api_surface = WIKI_API_SURFACE_PATH.read_text(encoding="utf-8")
    mesh_products = WIKI_MESH_PRODUCTS_PATH.read_text(encoding="utf-8")
    repo_context = REPO_CONTEXT_PATH.read_text(encoding="utf-8")

    assert "advisory.proposals.reviewed_narrative_evidence" in api_surface
    assert "advisory_proposal_reviewed_narrative_evidence" in api_surface
    assert "Client-ready publication" in api_surface
    assert "lotus-advise:ProposalNarrativeEvidence:v1" in mesh_products
    assert "proposal-narrative-evidence.telemetry.v1.json" in mesh_products
    assert "ProposalNarrativeEvidence:v1" in repo_context
    assert "client-ready publication, and external client communication" in repo_context
    assert "supported RFC-0023 closure claims" in repo_context
