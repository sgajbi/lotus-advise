from __future__ import annotations

from pathlib import Path

RFC26_PATH = Path("docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0026_records_current_prerequisites_and_readiness_boundary() -> None:
    rfc = _flat(RFC26_PATH)

    required_markers = (
        "IMPLEMENTED for source-owned first-wave advisor cockpit operating workflow",
        "Last Tightened** | 2026-05-31",
        "rfc0026-advisor-cockpit-gold-standard",
        "2026-05-27 Implementation Readiness Decision",
        "RFC-0023 is implemented for advisor-review proposal narrative evidence",
        "RFC-0024 is implemented for advisor-use proposal memo evidence",
        "RFC-0025 is implemented for advisor/compliance policy evaluation evidence",
        "AdvisoryPolicyEvaluationRecord:v1",
        "Completed approval/waiver authority",
        "client-ready policy publication",
        "Each implementation slice must be finished, tested, reviewed, committed",
    )
    for marker in required_markers:
        assert marker in rfc


def test_rfc0026_requires_repeatable_front_office_cockpit_automation() -> None:
    rfc = _flat(RFC26_PATH)

    required_markers = (
        "Canonical Front-Office Automation Expansion",
        "RFC26_ADVISOR_COCKPIT_POLICY_ACTION_CANONICAL",
        "PB_SG_GLOBAL_BAL_001",
        "RFC23_25_ADVISORY_PROPOSAL_POLICY_CANONICAL",
        "SG_PRIVATE_BANKING_REFERENCE",
        "ADVISOR_COCKPIT_CANONICAL_VALIDATED",
        "scripts/live/validation/advisor-cockpit-proof.mjs",
        "npm run live:stack:up:validate",
        "acknowledgement idempotency proof",
        "Gateway proof that source-owned priorities",
        "Workbench browser proof that the cockpit is Gateway-first",
        "lowest useful automated test layer",
    )
    for marker in required_markers:
        assert marker in rfc


def test_rfc0026_slice_zero_decisions_are_closed_before_implementation() -> None:
    rfc = _flat(RFC26_PATH)

    assert "## 25. Slice 0 Implementation Decisions" in _read(RFC26_PATH)
    assert "## 25. Open Questions" not in _read(RFC26_PATH)

    required_decisions = (
        "Support advisor, desk head, compliance reviewer, operations reviewer, and demo/read-only",
        "SOURCE_READINESS_GAP",
        "First wave supports portfolio and proposal contexts",
        "Default page size is 25, maximum page size is 100",
        (
            "advisor book with at least 100 portfolios, 250 proposals or proposal-like "
            "work items, 500 action items"
        ),
        "RFC-0028 owns full bank-demo/RFP packaging",
    )
    for marker in required_decisions:
        assert marker in rfc


def test_rfc_index_and_wiki_reflect_rfc0026_closure_and_rfc0027_completion() -> None:
    rfc_index = _read(RFC_INDEX_PATH)
    wiki_index = _flat(WIKI_RFC_INDEX_PATH)
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    assert (
        "RFC-0026 | Advisor Cockpit Operating Workflow | "
        "IMPLEMENTED for source-owned first-wave advisor cockpit operating workflow" in rfc_index
    )
    assert "- `RFC-0025` advisor/compliance policy evidence" in rfc_index
    assert "- `RFC-0026` source-owned first-wave advisor cockpit operating workflow" in rfc_index

    not_yet_implemented = rfc_index.split("## Not Yet Implemented", maxsplit=1)[1].split(
        "Recommended near-term implementation order", maxsplit=1
    )[0]
    assert "- `RFC-0025`" not in not_yet_implemented
    assert "- `RFC-0026`" not in not_yet_implemented
    assert "- `RFC-0027`" not in not_yet_implemented
    assert "- `RFC-0028`" not in not_yet_implemented
    assert (
        "RFC-0028 | Bank Demo Journey and Client-Ready Proof | "
        "IMPLEMENTED - bank-demo proof and claim-controlled commercial material complete"
        in rfc_index
    )

    assert "RFC-0026 is implemented" in wiki_index
    expected_rfc27_wiki_status = (
        "RFC-0027 is implemented for governed internal advisor/reviewer copilot interactions"
    )
    assert expected_rfc27_wiki_status in wiki_index
    assert "RFC-0028 is implemented for repeatable bank-demo proof" in wiki_index
    assert "RFC26_ADVISOR_COCKPIT_POLICY_ACTION_CANONICAL" in wiki_index
    assert "Implemented for the source-owned first-wave advisor cockpit" in supported_features
    assert "AdvisorCockpitOperatingSnapshot:v1" in supported_features


def test_rfc0026_supported_features_ledger_reflects_implemented_closure_truth() -> None:
    rfc = _read(RFC26_PATH)
    ledger = rfc.split("## 20. Supported-Features Ledger", maxsplit=1)[1].split(
        "## 21. Acceptance Criteria", maxsplit=1
    )[0]
    flat_ledger = " ".join(ledger.split())

    assert "Current support posture" in ledger
    assert "Initial RFC state" not in ledger
    assert "| Advisor cockpit snapshot | Supported for source-owned first-wave" in ledger
    assert "| Advisory action item register | Supported |" in ledger
    gateway_surface_marker = (
        "| Gateway/Workbench advisor cockpit | Supported for the canonical first-wave surface |"
    )
    assert gateway_surface_marker in ledger
    assert "| Cockpit data products | Supported |" in ledger
    assert "Client-ready publication and external client communication remain blocked" in (
        flat_ledger
    )
    assert "OMS order/fill/settlement support remains unsupported" in flat_ledger
    assert "| Proposed |" not in ledger
