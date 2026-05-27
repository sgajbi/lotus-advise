from __future__ import annotations

from pathlib import Path

RFC26_PATH = Path("docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md")
SLICE4_PATH = Path("docs/rfcs/RFC-0026-slice-4-cockpit-domain-model-and-vocabulary.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
ACTION_FACTORY_PATH = Path("src/core/advisor_cockpit/action_factory.py")
BEHAVIOR_TEST_PATH = Path(
    "tests/unit/advisory/engine/test_engine_advisor_cockpit_action_factory.py"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0026_slice4_evidence_is_indexed() -> None:
    source_ref = "docs/rfcs/RFC-0026-slice-4-cockpit-domain-model-and-vocabulary.md"

    assert source_ref in _read(RFC26_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)


def test_rfc0026_slice4_records_non_promoting_action_factory_posture() -> None:
    slice4 = _flat(SLICE4_PATH)
    supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    required_markers = (
        "IMPLEMENTED - SOURCE-BACKED ACTION CONSTRUCTION",
        "`src/core/advisor_cockpit/action_factory.py`",
        "does not expose cockpit APIs",
        "no data product or trust telemetry is promoted",
        "Gateway and Workbench behavior remains unimplemented until their owning slices",
        "not deferral outside RFC-0026",
        "mandatory subsequent RFC-0026 slices",
    )
    for marker in required_markers:
        assert marker in slice4

    assert "source-backed action construction" in supported
    assert "Implemented for the source-owned first-wave advisor cockpit" in supported


def test_rfc0026_slice4_contract_is_backed_by_code_and_behavior_tests() -> None:
    action_factory = _read(ACTION_FACTORY_PATH)
    behavior_tests = _read(BEHAVIOR_TEST_PATH)

    required_builders = (
        "build_source_backed_action",
        "build_policy_review_required_action",
        "build_memo_package_blocked_action",
        "build_meeting_preparation_action",
        "build_supportability_degraded_action",
        "build_unsupported_capability_action",
        "build_first_wave_cockpit_actions",
    )
    for builder in required_builders:
        assert f"def {builder}" in action_factory
        assert builder in behavior_tests

    for marker in (
        "POLICY_REVIEW_REQUIRED",
        "MEMO_PACKAGE_BLOCKED",
        "CLIENT_MEETING_PREPARATION",
        "SUPPORTABILITY_DEGRADED",
        "UNSUPPORTED_CAPABILITY",
        "CLIENT_READY_PUBLICATION",
        "CLIENT_READY_BLOCKED",
    ):
        assert marker in action_factory
        assert marker in behavior_tests
