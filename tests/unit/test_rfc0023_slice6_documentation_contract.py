from __future__ import annotations

from pathlib import Path

RFC_PATH = Path(
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)
SLICE6_PATH = Path(
    "docs/rfcs/RFC-0023-slice-6-narrative-policy-disclosure-and-guardrail-framework.md"
)
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0023_slice6_policy_guardrail_baseline_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice6_text = SLICE6_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0023-slice-6-narrative-policy-disclosure-and-guardrail-framework.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Implementation",
        "## Supported Request Shape",
        "## Supported Response Shape",
        "## Disclosure Rules",
        "## Guardrail Rules",
        "## Client-Ready Blocking",
        "## Non-Promoted Behavior",
    ):
        assert section in slice6_text

    assert "IMPLEMENTED - POLICY, DISCLOSURE, AND GUARDRAIL BASELINE" in slice6_text
    assert "advisory-narrative-policy.2026-05" in slice6_text


def test_rfc0023_slice6_supported_features_promote_only_metadata_not_client_ready() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "Slices 0-6 complete" in supported_features
    assert "policy/disclosure/guardrail baseline" in supported_features
    assert "deterministic policy, disclosure, and guardrail metadata" in supported_features
    assert "client-ready commentary remain gated" in supported_features
    assert "Client-ready proposal commentary | Supported" not in supported_features


def test_rfc0023_slice6_documents_non_promoted_behavior() -> None:
    slice6_text = SLICE6_PATH.read_text(encoding="utf-8")

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
        assert blocked in slice6_text
