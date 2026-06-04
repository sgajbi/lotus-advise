from __future__ import annotations

from pathlib import Path

RFC26_PATH = Path("docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md")
SLICE5_PATH = Path("docs/rfcs/RFC-0026-slice-5-source-read-model-and-aggregation.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
SOURCE_READ_MODEL_PATH = Path("src/core/advisor_cockpit/source_read_model.py")
SOURCE_PROJECTION_PATH = Path("src/core/advisor_cockpit/source_projection.py")
SOURCE_POLICY_MEMO_PROJECTION_PATH = Path(
    "src/core/advisor_cockpit/source_projection_policy_memo.py"
)
BEHAVIOR_TEST_PATH = Path(
    "tests/unit/advisory/engine/test_engine_advisor_cockpit_source_read_model.py"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0026_slice5_evidence_is_indexed() -> None:
    source_ref = "docs/rfcs/RFC-0026-slice-5-source-read-model-and-aggregation.md"

    assert source_ref in _read(RFC26_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)


def test_rfc0026_slice5_records_non_promoting_source_aggregation_posture() -> None:
    slice5 = _flat(SLICE5_PATH)
    supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    required_markers = (
        "IMPLEMENTED - PRELOADED SOURCE AGGREGATION",
        "`src/core/advisor_cockpit/source_read_model.py`",
        "does not expose cockpit APIs",
        "no data product, trust telemetry, or `/platform/capabilities` claim is promoted",
        "not deferral outside RFC-0026",
        "mandatory subsequent RFC-0026 slices",
    )
    for marker in required_markers:
        assert marker in slice5

    assert "source-read-model aggregation" in supported
    assert "Implemented for the source-owned advisor cockpit" in supported


def test_rfc0026_slice5_contract_is_backed_by_code_and_behavior_tests() -> None:
    source_read_model = _read(SOURCE_READ_MODEL_PATH)
    source_projection = _read(SOURCE_PROJECTION_PATH)
    source_policy_memo_projection = _read(SOURCE_POLICY_MEMO_PROJECTION_PATH)
    source_contract = f"{source_read_model}\n{source_projection}\n{source_policy_memo_projection}"
    behavior_tests = _read(BEHAVIOR_TEST_PATH)

    required_markers = (
        "AdvisorCockpitSourceBatch",
        "AdvisorCockpitSourceReadModel",
        "build_advisor_cockpit_source_read_model",
        "ACTIVE_PROPOSAL_STATES",
        "COCKPIT_POLICY_REVIEW_STATUSES",
        "ProposalRecord",
        "ProposalMemoRecord",
        "PolicyEvaluationRecord",
    )
    for marker in required_markers:
        assert marker in source_contract
        assert marker in behavior_tests

    for marker in (
        "PENDING_REVIEW",
        "BLOCKED",
        "MEMO_REVIEW_REQUIRED",
        "MEMO_FINALIZATION_REQUIRED",
        "source_counts",
        "lineage_id",
    ):
        assert marker in source_contract
        assert marker in behavior_tests
