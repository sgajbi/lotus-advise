from __future__ import annotations

from pathlib import Path

RFC26_PATH = Path("docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md")
SLICE6_PATH = Path("docs/rfcs/RFC-0026-slice-6-priority-sla-acknowledgement-rules.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
RULES_PATH = Path("src/core/advisor_cockpit/rules.py")
BEHAVIOR_TEST_PATH = Path("tests/unit/advisory/engine/test_engine_advisor_cockpit_rules.py")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0026_slice6_evidence_is_indexed() -> None:
    source_ref = "docs/rfcs/RFC-0026-slice-6-priority-sla-acknowledgement-rules.md"

    assert source_ref in _read(RFC26_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)


def test_rfc0026_slice6_records_non_promoting_rule_posture() -> None:
    slice6 = _flat(SLICE6_PATH)
    supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    required_markers = (
        "IMPLEMENTED - DETERMINISTIC SLA AND ACKNOWLEDGEMENT POSTURE",
        "`src/core/advisor_cockpit/rules.py`",
        "does not expose cockpit APIs",
        "no acknowledgement persistence is added",
        "no data product, trust telemetry, or `/platform/capabilities` claim is promoted",
        "not deferral outside RFC-0026",
        "mandatory subsequent RFC-0026 slices",
    )
    for marker in required_markers:
        assert marker in slice6

    assert "deterministic SLA/acknowledgement rules" in supported
    assert "Implemented for the source-owned advisor cockpit" in supported


def test_rfc0026_slice6_contract_is_backed_by_code_and_behavior_tests() -> None:
    rules = _read(RULES_PATH)
    behavior_tests = _read(BEHAVIOR_TEST_PATH)

    required_markers = (
        "derive_cockpit_sla_age_band",
        "with_cockpit_sla_age_band",
        "apply_cockpit_acknowledgement_state",
        "is_cockpit_action_owner_blocking",
        "OWNER_BLOCKING_STATUSES",
        "DUE_SOON_WINDOW",
        "DUE_NOW_GRACE_WINDOW",
        "CRITICAL_OVERDUE_WINDOW",
    )
    for marker in required_markers:
        assert marker in rules
        assert marker in behavior_tests

    for marker in (
        "NOT_APPLICABLE",
        "NOT_DUE",
        "DUE_SOON",
        "DUE_NOW",
        "OVERDUE",
        "CRITICAL_OVERDUE",
        "acknowledgement_state",
    ):
        assert marker in behavior_tests
