from __future__ import annotations

from pathlib import Path

RFC_PATH = Path(
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)
SLICE10_PATH = Path("docs/rfcs/RFC-0023-slice-10-certified-api-and-openapi.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0023_slice10_certified_api_baseline_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice10_text = SLICE10_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0023-slice-10-certified-api-and-openapi.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Outcome",
        "## OpenAPI Contract",
        "## Behavior Certification",
        "## Non-Promoted Behavior",
        "## Acceptance Gate",
    ):
        assert section in slice10_text

    assert "IMPLEMENTED - CERTIFIED API AND OPENAPI BASELINE" in slice10_text
    assert "stale-route absence" in slice10_text
    assert "material returned-field coverage" in slice10_text


def test_rfc0023_slice10_supported_features_promote_only_certified_advisor_review_api() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "Slices 0-10 complete" in supported_features
    assert "certified canonical API/OpenAPI route inventory" in supported_features
    assert "standalone narrative read/regeneration routes" in supported_features
    assert "Client-ready proposal commentary | Supported" not in supported_features


def test_rfc0023_slice10_documents_non_promoted_behavior() -> None:
    slice10_text = SLICE10_PATH.read_text(encoding="utf-8")

    for blocked in (
        "standalone narrative read endpoints",
        "standalone narrative regeneration endpoints",
        "compliance-review, client-draft, or client-ready narrative states",
        "report/render/archive artifact inclusion",
        "Gateway or Workbench rendering",
        "narrative data-product or trust-telemetry promotion",
        "`/platform/capabilities` narrative feature promotion",
        "sales/demo-safe narrative proof",
    ):
        assert blocked in slice10_text
