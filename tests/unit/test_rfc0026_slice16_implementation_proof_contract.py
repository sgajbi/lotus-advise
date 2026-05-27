from __future__ import annotations

from pathlib import Path

SLICE16_PATH = Path("docs/rfcs/RFC-0026-slice-16-implementation-proof.md")
RFC26_PATH = Path("docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0026_slice16_evidence_is_indexed() -> None:
    source_ref = "docs/rfcs/RFC-0026-slice-16-implementation-proof.md"

    assert source_ref in _read(RFC26_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)


def test_rfc0026_slice16_records_hardened_live_proof() -> None:
    slice16 = _flat(SLICE16_PATH)

    for marker in (
        "IMPLEMENTED - LIVE CANONICAL PROOF HARDENED",
        "PB_SG_GLOBAL_BAL_001",
        "ADVISOR_COCKPIT_ACTION_ACKNOWLEDGED",
        "paginationCursor",
        "roleProjectionValidated",
        "houseViewCohortId",
        "preparationPacketCount",
        "preparationPacketRouteCount",
        "clientReadyPublication: BLOCKED",
        "ADVISE_GATEWAY_WORKBENCH_CANONICAL_PROOF_SUPPORTED",
        "CANONICAL_WORKBENCH_PROOF_PASSED_RFC0026",
    ):
        assert marker in slice16


def test_rfc0026_slice16_records_live_defects_and_right_layer_tests() -> None:
    slice16 = _flat(SLICE16_PATH)

    for marker in (
        "Stale Gateway image",
        "tests/unit/live-canonical-validation-script.test.ts",
        "Portfolio-scoped cockpit preparation",
        "tests/unit/advisory/engine/test_engine_advisor_cockpit_service.py",
        "Memo/report-derived cockpit actions lost portfolio scope",
        "tests/unit/advisory/engine/test_engine_advisor_cockpit_source_read_model.py",
        "tactical house-view cockpit actions returned no lineage refs",
        (
            "Execution-status and other source-backed cockpit actions could be emitted "
            "without lineage refs"
        ),
        "tests/unit/advisory/engine/test_engine_advisor_cockpit_action_factory.py",
        "lower-level automated test before live validation was rerun",
    ):
        assert marker in slice16


def test_rfc0026_slice16_preserves_claim_boundaries() -> None:
    docs = "\n".join((_flat(SLICE16_PATH), _flat(RFC26_PATH), _flat(WIKI_RFC_INDEX_PATH)))

    for marker in (
        "client-ready publication",
        "completed policy approval or sign-off authority",
        "CRM system-of-record behavior",
        "external client communication",
        "OMS orders, fills, settlement",
        "DPM campaign creation",
        "full RFC-0028 demo/RFP package readiness",
    ):
        assert marker in docs
