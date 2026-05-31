from __future__ import annotations

from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_rfc0025_has_executable_gold_standard_slice_plan() -> None:
    rfc = _read(RFC_PATH)

    assert "IMPLEMENTED for advisor/compliance policy evaluation evidence" in rfc
    assert "2026-05-26" in rfc

    required_slice_headings = (
        "### Slice 0 - Critical Review, Source Map, and Product Gap Allocation",
        "### Slice 1 - Platform Automation and Scaffolding Improvement",
        "### Slice 2 - Cleanup and Structure",
        "### Slice 3 - Data Product and Platform Hardening",
        "### Slice 14 - Implementation Proof",
        "### Slice 15 - Second-Last Hardening and Review",
        "### Slice 16 - Final Closure",
        "### Slice 17 - Post-Completion Communication",
    )
    for heading in required_slice_headings:
        assert heading in rfc

    assert "all repo and cross-repo PRs are merged" in rfc
    assert 'no broad "later", WTBD, or side-ledger dependency' in rfc
    assert "small, meaningful commit" in rfc


def test_rfc0025_resolves_preimplementation_decisions_before_coding() -> None:
    rfc = _read(RFC_PATH)
    flat_rfc = _flat(rfc)

    assert "## 25. Slice 0 Pre-Implementation Decisions" in rfc
    assert "## 25. Open Questions" not in rfc

    required_decisions = (
        "GLOBAL_PRIVATE_BANKING_BASELINE",
        "SG_PRIVATE_BANKING_REFERENCE",
        "PB_SG_GLOBAL_BAL_001",
        "Client-ready publication stays blocked",
        "`lotus-core` is the source authority",
        "`lotus-risk` is the source authority",
        "RFC-0025 consumes only implementation-backed RFC-0016 or owner-repo evidence",
        "No local-only policy scaffold may be introduced before Slice 1",
    )
    for decision in required_decisions:
        assert decision in flat_rfc

    assert "defaulted to suitable, eligible, or best-interest" in flat_rfc
    assert (
        "AI may summarize policy evidence but cannot satisfy, waive, approve, hide, or reclassify"
        in flat_rfc
    )


def test_rfc0025_documentation_as_product_and_supported_claim_controls_are_pinned() -> None:
    rfc = _read(RFC_PATH)
    supported = _read(WIKI_SUPPORTED_FEATURES_PATH)
    flat_rfc = _flat(rfc)

    assert "## 18. Documentation-as-Product Requirements" in rfc
    assert (
        "developers, business users, compliance, operations, sales/pre-sales, and demo preparation"
        in flat_rfc
    )
    assert (
        "Supported-features wording changes only after implementation-backed support exists" in rfc
    )
    assert "wiki, demo notes, API examples, architecture diagram, operator guidance" in rfc
    assert "no document can imply the sample/reference packs are legal advice" in rfc

    assert "`RFC-0025` | Enterprise suitability and best-interest policy packs" in supported
    assert "RFC-0025 is implemented for advisor/compliance policy evidence through Slice 17" in (
        supported
    )
    assert "Slice 17 completes post-completion communication" in supported
    assert "client-ready publication and external communication remain gated" in supported
    policy_feature_row = (
        "AdvisoryPolicyEvaluationRecord:v1 | Supported for advisor/compliance policy evidence"
    )
    assert policy_feature_row in supported


def test_rfc_and_wiki_indexes_point_past_rfc0025_without_stale_future_claim() -> None:
    rfc_index = _read(RFC_INDEX_PATH)
    wiki_index = _read(WIKI_RFC_INDEX_PATH)
    flat_wiki_index = _flat(wiki_index)

    assert (
        "RFC-0028 | Bank Demo Journey and Client-Ready Proof | "
        "IMPLEMENTED - bank-demo proof and claim-controlled commercial material complete"
        in rfc_index
    )
    assert "- `RFC-0025` advisor/compliance policy evidence" in rfc_index
    assert "RFC-0024 is implemented for advisor-use proposal memo evidence" in flat_wiki_index
    assert "RFC-0025 is implemented for advisor/compliance policy evaluation evidence" in (
        flat_wiki_index
    )
    assert "RFC-0025 Slice 17 is implemented as post-completion communication" in wiki_index
    assert "RFC-0024 is the next recommended implementation slice" not in wiki_index
    assert (
        "RFC-0025 enterprise suitability and best-interest policy packs"
        not in rfc_index.split(
            "Recommended near-term implementation order:",
            maxsplit=1,
        )[1]
    )

    active_future_section = wiki_index.split("## Active Future Work", maxsplit=1)[1].split(
        "## Important Interpretation",
        maxsplit=1,
    )[0]
    assert "RFC-0024 advisor proposal memo and evidence pack" not in active_future_section
    assert "RFC-0025 enterprise suitability and best-interest policy packs" not in (
        active_future_section
    )
    assert "RFC-0028 bank demo journey and client-ready proof" not in active_future_section
    assert "RFC-0026 advisor cockpit operating workflow" not in active_future_section
    assert "RFC-0027 governed advisory AI copilot" not in active_future_section
    assert "RFC-0028 is implemented for repeatable bank-demo proof" in flat_wiki_index
