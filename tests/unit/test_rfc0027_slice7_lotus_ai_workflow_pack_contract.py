from __future__ import annotations

from pathlib import Path

RFC27_PATH = Path("docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md")
SLICE7_PATH = Path("docs/rfcs/RFC-0027-slice-7-lotus-ai-workflow-pack-model-risk-controls.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0027_slice7_evidence_is_indexed_and_non_promoting() -> None:
    source_ref = "docs/rfcs/RFC-0027-slice-7-lotus-ai-workflow-pack-model-risk-controls.md"

    assert source_ref in _read(RFC27_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)

    slice7 = _read(SLICE7_PATH)
    flat_supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    assert "IMPLEMENTED - ADAPTER AND WORKFLOW-PACK EXECUTION SEAM ONLY" in slice7
    assert "does not expose Advise copilot APIs" in slice7
    assert "Slice 7 adds governed `lotus-ai` workflow-pack execution" in flat_supported
    assert "without Advise API, Gateway, Workbench, data-product, canonical proof" in (
        flat_supported
    )
    assert "before any supported copilot claim is promoted" in flat_supported


def test_rfc0027_slice7_records_workflow_pack_and_model_risk_evidence() -> None:
    flat_slice7 = _flat(SLICE7_PATH)

    required = (
        "advisory_copilot_proposal_explanation.pack@v1",
        "advisory_copilot_evidence_qa.pack@v1",
        "advisory_copilot_meeting_preparation.pack@v1",
        "advisory_copilot_compliance_review_summary.pack@v1",
        "advisory_copilot_operations_report_handoff.pack@v1",
        "advisory_copilot_client_follow_up_draft.pack@v1",
        "advisory-copilot-lotus-ai-adapter.v1",
        "advisory-copilot-instructions.v1",
        "advisory-copilot-output-schema.v1",
        "advisory-copilot-eval-pack.v1",
        "tests/unit/advisory/api/test_lotus_ai_advisory_copilot.py",
    )
    for item in required:
        assert item in flat_slice7
