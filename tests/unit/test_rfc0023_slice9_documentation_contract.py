from __future__ import annotations

from pathlib import Path

RFC_PATH = Path(
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)
SLICE9_PATH = Path(
    "docs/rfcs/RFC-0023-slice-9-alternatives-decision-summary-and-policy-evidence-integration.md"
)
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0023_slice9_evidence_integration_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice9_text = SLICE9_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = (
        "docs/rfcs/"
        "RFC-0023-slice-9-alternatives-decision-summary-and-policy-evidence-integration.md"
    )
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Outcome",
        "## Evidence Flow",
        "## Section Behavior",
        "## Implementation Evidence",
        "## Non-Promoted Behavior",
        "## Acceptance Gate",
    ):
        assert section in slice9_text

    assert "IMPLEMENTED - DECISION SUMMARY" in slice9_text
    assert "RFC-0021 proposal_decision_summary" in slice9_text
    assert "RFC-0022 proposal_alternatives" in slice9_text


def test_rfc0023_slice9_supported_features_promote_only_advisor_review_enrichment() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "Slices 0-10 complete" in supported_features
    assert "decision-summary/alternatives-aware section rendering" in supported_features
    assert "selected-alternative tradeoffs" in supported_features
    assert "risk/suitability limitation wording" in supported_features
    assert "Client-ready proposal commentary | Supported" not in supported_features


def test_rfc0023_slice9_documents_non_promoted_behavior() -> None:
    slice9_text = SLICE9_PATH.read_text(encoding="utf-8")

    for blocked in (
        "standalone narrative read/regeneration endpoints",
        "compliance-review, client-draft, or client-ready narrative states",
        "report/render/archive artifact inclusion",
        "Gateway or Workbench rendering",
        "`/platform/capabilities` narrative feature promotion",
        "narrative data-product or trust-telemetry promotion",
        "sales/demo-safe narrative proof",
    ):
        assert blocked in slice9_text
