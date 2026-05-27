from __future__ import annotations

from pathlib import Path

SLICE13_PATH = Path("docs/rfcs/RFC-0026-slice-13-data-product-capability-promotion.md")
RFC26_PATH = Path("docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
README_PATH = Path("README.md")
REPO_CONTEXT_PATH = Path("REPOSITORY-ENGINEERING-CONTEXT.md")
WIKI_API_PATH = Path("wiki/API-Surface.md")
WIKI_ARCHITECTURE_PATH = Path("wiki/Architecture.md")
WIKI_OPERATIONS_PATH = Path("wiki/Operations-Runbook.md")
CAPABILITIES_PATH = Path("src/api/capabilities/service.py")
COCKPIT_SERVICE_PATH = Path("src/core/advisor_cockpit/service.py")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0026_slice13_evidence_is_indexed() -> None:
    source_ref = "docs/rfcs/RFC-0026-slice-13-data-product-capability-promotion.md"

    assert source_ref in _read(RFC26_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)


def test_rfc0026_slice13_records_promotion_and_boundaries() -> None:
    slice13 = _flat(SLICE13_PATH)
    supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    required_markers = (
        "IMPLEMENTED - DATA PRODUCT AND CAPABILITY PROMOTION",
        "AdvisorCockpitOperatingSnapshot:v1",
        "AdvisoryActionItemRegister:v1",
        "advisory.advisor_cockpit",
        "advisor_cockpit_operating_workflow",
        "PB_SG_GLOBAL_BAL_001",
        "client-ready publication",
        "OMS orders, fills, or settlement",
        "full RFC-0028 demo/RFP package support",
    )
    for marker in required_markers:
        assert marker in slice13

    assert "Slice 13 promotes `AdvisorCockpitOperatingSnapshot:v1`" in supported
    assert "completed policy approval authority" in supported


def test_rfc0026_slice13_updates_operator_and_repository_truth() -> None:
    docs = "\n".join(
        (
            _flat(README_PATH),
            _flat(REPO_CONTEXT_PATH),
            _flat(WIKI_API_PATH),
            _flat(WIKI_ARCHITECTURE_PATH),
            _flat(WIKI_OPERATIONS_PATH),
        )
    )

    for marker in (
        "AdvisorCockpitOperatingSnapshot:v1",
        "AdvisoryActionItemRegister:v1",
        "PB_SG_GLOBAL_BAL_001",
        "GET /advisory/cockpit/supportability",
        "GET /platform/capabilities",
        "CRM system-of-record",
        "OMS order",
        "completed policy approval authority",
        "full RFC-0028 demo/RFP",
    ):
        assert marker in docs


def test_rfc0026_slice13_code_paths_promote_capability_and_supportability() -> None:
    capabilities = _read(CAPABILITIES_PATH)
    cockpit_service = _read(COCKPIT_SERVICE_PATH)

    for marker in (
        "advisory.advisor_cockpit",
        "advisor_cockpit_operating_workflow",
        "Gateway/Workbench canonical proof",
        "ADVISORY_LIFECYCLE_DISABLED",
    ):
        assert marker in capabilities

    for marker in (
        "SUPPORTED_BY_LOTUS_GATEWAY_RFC0026",
        "CANONICAL_WORKBENCH_PROOF_PASSED_RFC0026",
        "ACTIVE_ADVISOR_COCKPIT_PRODUCTS_RFC0026",
        "PB_SG_GLOBAL_BAL_001_ADVISOR_COCKPIT_VALIDATED",
    ):
        assert marker in cockpit_service
