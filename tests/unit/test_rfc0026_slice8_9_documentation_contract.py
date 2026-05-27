from __future__ import annotations

from pathlib import Path

RFC26_PATH = Path("docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
SLICE8_PATH = Path("docs/rfcs/RFC-0026-slice-8-meeting-preparation-client-follow-up.md")
SLICE9_PATH = Path("docs/rfcs/RFC-0026-slice-9-supervisory-approval-compliance-queues.md")
SLICE10_PATH = Path("docs/rfcs/RFC-0026-slice-10-readiness-execution-house-view.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_rfc0026_slice8_and_slice9_evidence_is_indexed() -> None:
    for source_ref in (
        "docs/rfcs/RFC-0026-slice-8-meeting-preparation-client-follow-up.md",
        "docs/rfcs/RFC-0026-slice-9-supervisory-approval-compliance-queues.md",
        "docs/rfcs/RFC-0026-slice-10-readiness-execution-house-view.md",
    ):
        assert source_ref in _read(RFC26_PATH)
        assert source_ref in _read(RFC_INDEX_PATH)
        assert source_ref in _read(WIKI_RFC_INDEX_PATH)


def test_rfc0026_slice8_records_preparation_and_follow_up_boundaries() -> None:
    slice8 = _read(SLICE8_PATH)
    supported = _read(WIKI_SUPPORTED_FEATURES_PATH)

    for marker in (
        "GET /advisory/cockpit/preparation-packets",
        "ClientFollowUpActionSource",
        "EXTERNAL_CLIENT_COMMUNICATION",
        "CRM_SYSTEM_OF_RECORD",
        "client-ready publication",
    ):
        assert marker in slice8

    assert "Slice 8 adds paginated preparation packets and client follow-up actions" in supported


def test_rfc0026_slice9_records_supervisory_queue_boundaries() -> None:
    slice9 = _read(SLICE9_PATH)
    supported = _read(WIKI_SUPPORTED_FEATURES_PATH)

    for marker in (
        "ApprovalDependencyActionSource",
        "list_approvals_for_proposals",
        "`RISK_REVIEW`",
        "`COMPLIANCE_REVIEW`",
        "`AWAITING_CLIENT_CONSENT`",
        "completed approval/waiver authority",
    ):
        assert marker in slice9

    assert "Slice 9 adds source-backed risk, compliance, and consent queue projection" in supported


def test_rfc0026_slice10_records_downstream_readiness_boundaries() -> None:
    slice10 = _read(SLICE10_PATH)
    supported = _read(WIKI_SUPPORTED_FEATURES_PATH)

    for marker in (
        "ReportRenderArchiveActionSource",
        "ExecutionHandoffReadyActionSource",
        "ExecutionStatusAttentionActionSource",
        "HouseViewImpactActionSource",
        "OMS_ORDER_LIFECYCLE",
        "does not implement report rendering, archive storage, OMS orders",
    ):
        assert marker in slice10

    assert "Slice 10 adds report/archive readiness, execution handoff/status attention" in supported
