from __future__ import annotations

from pathlib import Path

RFC_PATH = Path(
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)
SLICE4_PATH = Path("docs/rfcs/RFC-0023-slice-4-data-product-and-supportability-baseline.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0023_slice4_data_product_baseline_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice4_text = SLICE4_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0023-slice-4-data-product-and-supportability-baseline.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Current Data-Product Evidence",
        "## Non-Promotion Decision",
        "## Future Promotion Rule",
        "## `/platform/capabilities` Baseline",
        "## Mesh and Trust Telemetry Baseline",
        "## Supportability Policy",
    ):
        assert section in slice4_text

    assert "IMPLEMENTED - NON-PROMOTION BASELINE" in slice4_text
    assert "does not promote a `ProposalNarrativeEvidence`" in slice4_text
    assert "decorative mesh claim" in slice4_text


def test_rfc0023_slice4_keeps_supported_features_non_claiming() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")
    slice4_text = SLICE4_PATH.read_text(encoding="utf-8")

    assert "Slices 0-9 complete" in supported_features
    assert "deterministic advisor-review artifact-path narrative" in supported_features
    assert "policy/disclosure/guardrail baseline" in supported_features
    assert "AI-assisted draft adapter baseline" in supported_features
    assert "proposal-version narrative review/replay baseline" in supported_features
    assert "compliance-review, client-draft, client-ready" in supported_features
    assert "Proposal narrative | Supported" not in supported_features
    assert "Client-ready proposal commentary | Supported" not in supported_features
    assert "`/platform/capabilities` feature" in supported_features
    assert "no `/platform/capabilities` response change" in slice4_text


def test_rfc0023_slice4_documents_data_product_promotion_blockers() -> None:
    slice4_text = SLICE4_PATH.read_text(encoding="utf-8")

    for blocker in (
        "no deterministic advisor-review narrative builder exists yet",
        "no persisted narrative version exists yet",
        "no narrative replay endpoint exists yet",
        "no review workflow exists",
        "no narrative source-input hash set exists yet",
        "no narrative guardrail result exists yet",
        "no report/render/archive lineage exists",
    ):
        assert blocker in slice4_text
