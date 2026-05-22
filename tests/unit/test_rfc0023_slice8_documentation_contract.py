from __future__ import annotations

from pathlib import Path

RFC_PATH = Path(
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)
SLICE8_PATH = Path(
    "docs/rfcs/RFC-0023-slice-8-review-workflow-persistence-idempotency-artifact-and-replay.md"
)
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0023_slice8_review_replay_baseline_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice8_text = SLICE8_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = (
        "docs/rfcs/RFC-0023-slice-8-review-workflow-persistence-idempotency-artifact-and-replay.md"
    )
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Outcome",
        "## Supported API Shape",
        "## Replay Contract",
        "## Client-Ready Boundary",
        "## Implementation Evidence",
        "## Non-Promoted Behavior",
        "## Acceptance Gate",
    ):
        assert section in slice8_text

    assert "IMPLEMENTED - REVIEW WORKFLOW" in slice8_text
    assert "NARRATIVE_REVIEWED" in slice8_text
    assert "IDEMPOTENCY_KEY_CONFLICT" in slice8_text


def test_rfc0023_slice8_supported_features_promote_only_review_replay_baseline() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "Slices 0-10 complete" in supported_features
    assert "proposal-version narrative review/replay baseline" in supported_features
    assert "version-scoped review events" in supported_features
    assert "source narrative hashes" in supported_features
    assert "exact persisted replay evidence" in supported_features
    assert "Client-ready proposal commentary | Supported" not in supported_features


def test_rfc0023_slice8_documents_non_promoted_behavior() -> None:
    slice8_text = SLICE8_PATH.read_text(encoding="utf-8")

    for blocked in (
        "standalone narrative read/regeneration endpoints",
        "mutable narrative text updates",
        "client-ready proposal commentary",
        "report/render/archive artifact inclusion",
        "Gateway or Workbench rendering",
        "`/platform/capabilities` narrative feature promotion",
        "narrative data-product or trust-telemetry promotion",
    ):
        assert blocked in slice8_text
