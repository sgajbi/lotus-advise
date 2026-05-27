from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app

RFC26_PATH = Path("docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md")
SLICE7_PATH = Path("docs/rfcs/RFC-0026-slice-7-certified-advise-apis.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
SERVICE_PATH = Path("src/core/advisor_cockpit/service.py")
ROUTES_PATH = Path("src/api/proposals/routes_advisor_cockpit.py")
MIGRATION_PATH = Path(
    "src/infrastructure/postgres_migrations/proposals/0008_cockpit_acknowledgements.sql"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0026_slice7_evidence_is_indexed() -> None:
    source_ref = "docs/rfcs/RFC-0026-slice-7-certified-advise-apis.md"

    assert source_ref in _read(RFC26_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)


def test_rfc0026_slice7_records_api_support_without_product_promotion() -> None:
    slice7 = _flat(SLICE7_PATH)
    supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    required_markers = (
        "IMPLEMENTED - ADVISE BACKEND API SUPPORT",
        "`AdvisorCockpitService`",
        "`AdvisorCockpitRepository`",
        "`list_memos_for_proposals`",
        "does not promote Gateway, Workbench, data products",
        "acknowledgement is idempotent and stale-version protected",
    )
    for marker in required_markers:
        assert marker in slice7 or marker in supported

    assert "Slice 7 adds Advise-owned cockpit action" in supported
    assert "no integrated advisor-cockpit product support claim is promoted" in supported.lower()


def test_rfc0026_slice7_code_paths_and_openapi_are_present() -> None:
    service = _read(SERVICE_PATH)
    routes = _read(ROUTES_PATH)
    migration = _read(MIGRATION_PATH)

    for marker in (
        "AdvisorCockpitService",
        "acknowledge_action",
        "save_cockpit_acknowledgement_with_idempotency",
        "COCKPIT_CONTRACT_VERSION",
        "ADVISOR_COCKPIT_ACTION_VERSION_STALE",
        "ADVISOR_COCKPIT_ACKNOWLEDGEMENT_IDEMPOTENCY_CONFLICT",
        "list_memos_for_proposals",
    ):
        assert marker in service

    for route in (
        "/advisory/cockpit/actions",
        "/advisory/cockpit/actions/{action_item_id}",
        "/advisory/cockpit/snapshot",
        "/advisory/cockpit/supportability",
        "/advisory/cockpit/actions/{action_item_id}/acknowledgements",
    ):
        assert route in routes

    assert "CREATE TABLE IF NOT EXISTS advisor_cockpit_acknowledgements" in migration
    assert "advisor_cockpit_acknowledgement_idempotency" in migration

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
    assert "/advisory/cockpit/actions" in schema["paths"]
    assert "/advisory/cockpit/supportability" in schema["paths"]
