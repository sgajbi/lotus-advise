from __future__ import annotations

from pathlib import Path

RFC_PATH = Path(
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)
SLICE7_PATH = Path("docs/rfcs/RFC-0023-slice-7-lotus-ai-adapter-and-ai-assisted-draft-baseline.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0023_slice7_ai_draft_baseline_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice7_text = SLICE7_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0023-slice-7-lotus-ai-adapter-and-ai-assisted-draft-baseline.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Implementation",
        "## Supported Request Shape",
        "## Lotus-AI Boundary",
        "## Supported Response Shape",
        "## Guardrail Rules",
        "## Non-Promoted Behavior",
        "## Acceptance Gate",
    ):
        assert section in slice7_text

    assert "IMPLEMENTED - AI-ASSISTED ADVISOR-REVIEW DRAFT BASELINE" in slice7_text
    assert "does not submit" in slice7_text
    assert "user-authored raw prompts" in slice7_text


def test_rfc0023_slice7_supported_features_promote_only_draft_ai_path() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "Slices 0-7 complete" in supported_features
    assert "AI-assisted draft adapter baseline" in supported_features
    assert "optional `AI_ASSISTED_DRAFT`" in supported_features
    assert "deterministic fallback" in supported_features
    assert "persisted/replayable, compliance-review" in supported_features
    assert "Proposal narrative | Supported" not in supported_features
    assert "Client-ready proposal commentary | Supported" not in supported_features


def test_rfc0023_slice7_documents_non_promoted_behavior() -> None:
    slice7_text = SLICE7_PATH.read_text(encoding="utf-8")

    for blocked in (
        "standalone narrative request/read/review/replay endpoints",
        "persisted narrative versions",
        "review approval or rejection actions",
        "compliance-review, client-draft, or client-ready narrative",
        "report/render/archive artifact inclusion",
        "`/platform/capabilities` narrative feature rows",
        "narrative data-product or trust-telemetry promotion",
        "demo-ready Workbench or report surfaces",
    ):
        assert blocked in slice7_text
