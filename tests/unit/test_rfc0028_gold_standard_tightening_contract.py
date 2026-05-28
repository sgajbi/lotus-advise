from __future__ import annotations

from pathlib import Path

RFC28_PATH = Path("docs/rfcs/RFC-0028-bank-demo-journey-and-client-ready-proof.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0028_locks_slice_zero_decisions_before_implementation() -> None:
    rfc = _read(RFC28_PATH)
    flat = _flat(RFC28_PATH)

    assert "Last Tightened** | 2026-05-28" in rfc
    assert "rfc0028-gold-standard-implementation" in rfc
    assert "## 22. Slice 0 Pre-Implementation Decisions" in rfc
    assert "## 22. Open Questions" not in rfc
    assert "No open implementation question remains for RFC-0028 Slice 1" in rfc

    required_decisions = (
        "Hybrid. `lotus-advise` must implement an Advise-owned proof-pack and supported-claim API",
        "Script-only proof is insufficient for RFC-0028",
        "Primary dataset is `PB_SG_GLOBAL_BAL_001`",
        "RFC28_BANK_DEMO_CLIENT_READY_PROOF_CANONICAL",
        "First supported journey is the combined private-banking advisory scenario",
        "No Workbench component may reconstruct advisory suitability, memo, narrative, policy",
        "CLIENT_READY_REVIEW_REQUIRED",
        "CLIENT_READY_PUBLICATION_BLOCKED",
        "External certifications, bank-specific control attestations, SOC/ISO status",
        "Load, latency, SLO, DR/RTO/RPO, tenant, and legal-entity claims block closure only",
        (
            "Produce markdown source now for demo script, proof interpretation guide, "
            "RFP/security pack"
        ),
    )
    for decision in required_decisions:
        assert decision in flat


def test_rfc0028_requires_canonical_front_office_automation_and_lowest_layer_tests() -> None:
    flat = _flat(RFC28_PATH)

    automation_markers = (
        "RFC-0028 must expand canonical front-office automation",
        "BANK_DEMO_PROOF_PACK_CREATED",
        "PB_SG_GLOBAL_BAL_001",
        "WorkBench evidence is not demo-ready",
    )
    for marker in automation_markers:
        assert marker.lower() in flat.lower()

    test_markers = (
        "Any live validation defect discovered during RFC-0028 must be covered",
        "unit for pure domain rules",
        "contract/API test for schema and route behavior",
        "integration test for cross-service contracts",
        "front-office/live validation for product-surface regressions",
    )
    for marker in test_markers:
        assert marker in flat


def test_rfc0028_records_platform_slice_one_supported_claim_scaffolding() -> None:
    flat = _flat(RFC28_PATH)

    markers = (
        "A reusable platform gap exists",
        "1f46cd764b1e8437091c6d5e567403053b899313",
        "ea6e8151d253f5d738dfb5902d8193238b946bba",
        "PR #366",
        "26554797152",
        "supported-claim-register.schema.json",
        "validate_supported_claim_register.py",
        "test_supported_claim_register_contract.py",
        "No Advise-local claim taxonomy may diverge from the platform validator",
    )
    for marker in markers:
        assert marker in flat


def test_rfc0028_indexes_record_platform_slice_one_without_promotion() -> None:
    rfc_index = _flat(RFC_INDEX_PATH)
    wiki_index = _flat(WIKI_RFC_INDEX_PATH)
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    index_markers = (
        "DRAFT - SLICES 0-1 COMPLETE",
        "RFC28_BANK_DEMO_CLIENT_READY_PROOF_CANONICAL",
        "BANK_DEMO_PROOF_PACK_CREATED",
        "PB_SG_GLOBAL_BAL_001",
        "PR #366",
        "26554797152",
    )
    for marker in index_markers:
        assert marker in rfc_index
        assert marker in wiki_index or marker in supported_features

    assert "No bank-demo/RFP or client-ready publication claim is promoted" in supported_features
    assert "full bank-demo/RFP and client-ready publication claims unpromoted" in wiki_index
    assert "DRAFT - SLICE 0 DECISIONS LOCKED" not in rfc_index
    assert "DRAFT - SLICE 0 DECISIONS LOCKED" not in wiki_index
    assert "Draft with Slice 0 decisions locked" not in supported_features


def test_rfc0028_records_slice_two_cleanup_scope_and_wiki_gate() -> None:
    flat = _flat(RFC28_PATH)

    markers = (
        "The first cleanup gap was durable documentation drift after Slice 1",
        "docs/rfcs/README.md",
        "wiki/RFC-Index.md",
        "wiki/Supported-Features.md",
        (
            "No Advise runtime code, controller, infrastructure module, "
            "or commercial asset was created"
        ),
        "Wiki source changed because supported-feature and RFC-index truth changed",
        "publication must happen after merge to `main`",
    )
    for marker in markers:
        assert marker in flat
