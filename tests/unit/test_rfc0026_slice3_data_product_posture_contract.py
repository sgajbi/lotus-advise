from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
DECLARATION_PATH = (
    REPO_ROOT / "contracts" / "domain-data-products" / "lotus-advise-products.v1.json"
)
TELEMETRY_DIR = REPO_ROOT / "contracts" / "trust-telemetry"
RFC26_PATH = REPO_ROOT / "docs" / "rfcs" / "RFC-0026-advisor-cockpit-operating-workflow.md"
SLICE3_PATH = (
    REPO_ROOT / "docs" / "rfcs" / "RFC-0026-slice-3-data-product-and-platform-hardening.md"
)
RFC_INDEX_PATH = REPO_ROOT / "docs" / "rfcs" / "README.md"
WIKI_RFC_INDEX_PATH = REPO_ROOT / "wiki" / "RFC-Index.md"
WIKI_SUPPORTED_FEATURES_PATH = REPO_ROOT / "wiki" / "Supported-Features.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_cockpit_data_products_are_promoted_after_canonical_runtime_evidence() -> None:
    declaration = json.loads(DECLARATION_PATH.read_text(encoding="utf-8"))
    products = {product["product_name"]: product for product in declaration["products"]}
    telemetry_files = {path.name for path in TELEMETRY_DIR.glob("*.json")}

    assert products["AdvisorCockpitOperatingSnapshot"]["lifecycle_status"] == "active"
    assert products["AdvisoryActionItemRegister"]["lifecycle_status"] == "active"
    assert "advisor-cockpit-operating-snapshot.telemetry.v1.json" in telemetry_files
    assert "advisory-action-item-register.telemetry.v1.json" in telemetry_files
    assert (
        "/advisory/cockpit/snapshot"
        in products["AdvisorCockpitOperatingSnapshot"]["current_routes"]
    )
    assert "/advisory/cockpit/actions" in products["AdvisoryActionItemRegister"]["current_routes"]
    assert "lotus-gateway" in products["AdvisorCockpitOperatingSnapshot"]["approved_consumers"]
    assert "lotus-workbench" in products["AdvisoryActionItemRegister"]["approved_consumers"]


def test_platform_capabilities_advertise_cockpit_after_runtime_support() -> None:
    with TestClient(app) as client:
        response = client.get("/platform/capabilities")

    assert response.status_code == 200
    payload = response.json()
    payload_text = json.dumps(payload, sort_keys=True).lower()
    feature_keys = {feature["key"] for feature in payload["features"]}
    workflow_keys = {workflow["workflow_key"] for workflow in payload["workflows"]}

    assert "advisory.advisor_cockpit" in feature_keys
    assert "advisor_cockpit_operating_workflow" in workflow_keys
    assert "advisor cockpit" in payload_text
    assert "client-ready publication" in payload_text


def test_rfc0026_slice3_evidence_is_indexed_and_non_promoting() -> None:
    source_ref = "docs/rfcs/RFC-0026-slice-3-data-product-and-platform-hardening.md"

    assert source_ref in _read(RFC26_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)

    slice3 = _flat(SLICE3_PATH)
    supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    assert "NON-PROMOTING DATA-PRODUCT POSTURE" in slice3
    assert "This is not deferral outside RFC-0026" in slice3
    assert "`AdvisorCockpitOperatingSnapshot:v1` may be promoted only after" in slice3
    assert "`AdvisoryActionItemRegister:v1` may be promoted only after" in slice3
    assert "AdvisorCockpitOperatingSnapshot:v1" in supported
    assert "AdvisoryActionItemRegister:v1" in supported
    assert "canonical `PB_SG_GLOBAL_BAL_001` proof" in supported


def test_rfc0026_slice3_records_mandatory_promotion_requirements() -> None:
    slice3 = _flat(SLICE3_PATH)

    required_markers = (
        "snapshot API exists and is OpenAPI-certified",
        "caller-context entitlement projection is server-side and tested",
        "Gateway preserves the Advise-owned cockpit contract",
        "Workbench consumes Gateway/BFF only",
        "canonical `RFC26_ADVISOR_COCKPIT_CANONICAL` proof passes",
        "cursor pagination, default page size 25, maximum page size 100",
        "acknowledgement writes are idempotent, audited, and stale-version protected",
        "live validation defects are covered by lower-layer tests before closure",
    )
    for marker in required_markers:
        assert marker in slice3
