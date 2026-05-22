from __future__ import annotations

from pathlib import Path

RFC_PATH = Path(
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)
SLICE5_PATH = Path(
    "docs/rfcs/RFC-0023-slice-5-grounding-packet-and-deterministic-template-baseline.md"
)
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0023_slice5_grounding_baseline_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice5_text = SLICE5_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = (
        "docs/rfcs/RFC-0023-slice-5-grounding-packet-and-deterministic-template-baseline.md"
    )
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Implementation",
        "## Supported Request Shape",
        "## Supported Response Shape",
        "## Grounding Rules",
        "## Missing Evidence",
        "## Non-Promoted Behavior",
    ):
        assert section in slice5_text

    assert "IMPLEMENTED - DETERMINISTIC ADVISOR-REVIEW BASELINE" in slice5_text
    assert "does not call `lotus-ai` or any model provider" in slice5_text


def test_rfc0023_slice5_supported_features_promote_only_artifact_path_narrative() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "Advisor-review proposal narrative" in supported_features
    assert "`POST /advisory/proposals/artifact` with `narrative_request`" in supported_features
    assert "deterministic policy, disclosure, and guardrail metadata" in supported_features
    assert "optional `AI_ASSISTED_DRAFT`" in supported_features
    assert "proposal-version narrative review/replay baseline" in supported_features
    assert "client-ready commentary" in supported_features
    assert "Proposal narrative | Supported" not in supported_features
    assert "Client-ready proposal commentary | Supported" not in supported_features


def test_rfc0023_slice5_documents_non_promoted_behavior() -> None:
    slice5_text = SLICE5_PATH.read_text(encoding="utf-8")

    for blocked in (
        "standalone narrative request/read/review/replay endpoints",
        "persisted narrative versions",
        "review approval or rejection actions",
        "AI-assisted generation",
        "compliance-review, client-draft, or client-ready narrative",
        "report/render/archive artifact inclusion",
        "`/platform/capabilities` narrative feature rows",
        "narrative data-product or trust-telemetry promotion",
    ):
        assert blocked in slice5_text
