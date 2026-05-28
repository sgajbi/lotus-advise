from __future__ import annotations

from pathlib import Path

RFC27_PATH = Path("docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md")
SLICE6_PATH = Path("docs/rfcs/RFC-0027-slice-6-guardrail-unsupported-evidence-engine.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0027_slice6_evidence_is_indexed_and_non_promoting() -> None:
    source_ref = "docs/rfcs/RFC-0027-slice-6-guardrail-unsupported-evidence-engine.md"

    assert source_ref in _read(RFC27_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)

    slice6 = _read(SLICE6_PATH)
    flat_supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    assert "IMPLEMENTED - PURE GUARDRAIL ENGINE ONLY" in slice6
    assert "does not invoke `lotus-ai`" in slice6
    assert "Those remain mandatory subsequent RFC-0027 slices" in slice6
    assert "Implemented for governed internal advisor/reviewer copilot interactions" in (
        flat_supported
    )
    assert "guardrail rejection for client-ready publication" in flat_supported
    assert "Client-ready publication, external client communication" in flat_supported


def test_rfc0027_slice6_records_guardrail_reason_coverage() -> None:
    flat_slice6 = _flat(SLICE6_PATH)

    coverage = (
        "autonomous advice or recommendation selection",
        "trade or order generation",
        "policy approval or waiver attempts",
        "client-ready publication or external client communication wording",
        "missing source refs",
        "prompt-injection markers",
        "raw prompts, provider responses, trace IDs, correlation IDs",
    )
    for item in coverage:
        assert item in flat_slice6

    tests = (
        "test_copilot_guardrail_evaluator_rejects_unsafe_requests_and_outputs",
        "test_copilot_guardrail_evaluator_allows_source_backed_review_request",
    )
    for test_name in tests:
        assert test_name in flat_slice6
