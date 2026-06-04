from __future__ import annotations

from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
SLICE2_PATH = Path("docs/rfcs/RFC-0025-slice-2-cleanup-and-structure-review.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
SUITABILITY_PATH = Path("src/core/common/suitability.py")
SUITABILITY_POST_TRADE_PATH = Path("src/core/common/suitability_post_trade_issues.py")
DECISION_SUMMARY_PATH = Path("src/core/advisory/decision_summary.py")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_rfc0025_slice2_evidence_is_indexed_and_non_claiming() -> None:
    source_ref = "docs/rfcs/RFC-0025-slice-2-cleanup-and-structure-review.md"

    assert source_ref in _read(RFC_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)

    slice2 = _read(SLICE2_PATH)
    supported = _read(WIKI_SUPPORTED_FEATURES_PATH)
    assert "NO RUNTIME POLICY-PACK CAPABILITY PROMOTED" in slice2
    assert "No policy-pack catalog, activation, validation, evaluation" in slice2
    assert "Slice 2 is complete as current-boundary cleanup only" in supported
    assert "Enterprise suitability and best-interest policy packs | Supported" not in supported


def test_rfc0025_slice2_pins_policy_context_boundary_cleanup() -> None:
    slice2 = _flat(_read(SLICE2_PATH))
    expected = (
        "policy-context status vocabulary and accessors",
        "The duplicate empty `_GLOBAL_PRIVATE_BANKING_BASELINE_PACK` definition was removed",
        "No empty RFC-0025 module tree was introduced",
        "Future RFC-0025 implementation slices must create dedicated modules",
    )

    for phrase in expected:
        assert phrase in slice2


def test_current_policy_context_is_not_reinterpreted_in_scanner_or_decision_summary() -> None:
    suitability = _read(SUITABILITY_PATH)
    suitability_post_trade = _read(SUITABILITY_POST_TRADE_PATH)
    decision_summary = _read(DECISION_SUMMARY_PATH)

    assert suitability.count("_GLOBAL_PRIVATE_BANKING_BASELINE_PACK = _SuitabilityPolicyPack") == 1
    assert 'client_context_status") == "AVAILABLE"' not in suitability
    assert 'mandate_context_status") == "AVAILABLE"' not in suitability
    assert 'client_context_status") == "AVAILABLE"' not in suitability_post_trade
    assert 'mandate_context_status") == "AVAILABLE"' not in suitability_post_trade
    assert "client_context_available(policy_context)" in suitability_post_trade
    assert "mandate_context_available(policy_context)" in suitability_post_trade
    assert 'client_context_status") == "AVAILABLE"' not in decision_summary
    assert 'mandate_context_status") == "AVAILABLE"' not in decision_summary
