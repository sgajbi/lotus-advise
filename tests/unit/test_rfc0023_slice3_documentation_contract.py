from __future__ import annotations

from pathlib import Path

RFC_PATH = Path(
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)
SLICE3_PATH = Path(
    "docs/rfcs/RFC-0023-slice-3-current-state-assessment-and-narrative-contract-baseline.md"
)
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0023_slice3_assessment_and_contract_baseline_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice3_text = SLICE3_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = (
        "docs/rfcs/RFC-0023-slice-3-current-state-assessment-and-narrative-contract-baseline.md"
    )
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Current-State Evidence Map",
        "## Deterministic Evidence Available Now",
        "## Additive Narrative Contract Baseline",
        "## API Vocabulary Reconciliation",
        "## No Public API v2 Required",
        "## First Implementation Scope",
    ):
        assert section in slice3_text

    assert "IMPLEMENTED - CONTRACT BASELINE ONLY" in slice3_text
    assert "does not implement generated proposal narrative" in slice3_text
    assert "No public API v2 is required" in slice3_text


def test_rfc0023_slice3_contract_baseline_keeps_supported_features_non_claiming() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")
    slice3_text = SLICE3_PATH.read_text(encoding="utf-8")

    assert "Slices 0-7 complete" in supported_features
    assert "deterministic advisor-review artifact-path narrative" in supported_features
    assert "data-product/supportability non-promotion baseline" in supported_features
    assert "policy/disclosure/guardrail baseline" in supported_features
    assert "AI-assisted draft adapter baseline" in supported_features
    assert "client-ready narrative remain gated" in supported_features
    assert "Proposal narrative | Supported" not in supported_features
    assert "Client-ready proposal commentary | Supported" not in supported_features
    assert "`ADVISOR_REVIEW`" in slice3_text
    assert "`CLIENT_READY` | Gated" in slice3_text


def test_rfc0023_slice3_documents_no_api_or_vocabulary_change_yet() -> None:
    slice3_text = SLICE3_PATH.read_text(encoding="utf-8")

    assert "This slice does not change OpenAPI or API vocabulary inventory" in slice3_text
    assert "No source route, model, persistence, capability, or OpenAPI contract is added" in (
        slice3_text
    )
    assert "`proposal_narrative`, not `ai_text`" in slice3_text
