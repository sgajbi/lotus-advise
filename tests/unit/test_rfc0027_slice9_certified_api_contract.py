from __future__ import annotations

from pathlib import Path

RFC27_PATH = Path("docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md")
SLICE9_PATH = Path("docs/rfcs/RFC-0027-slice-9-certified-advise-apis-openapi.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0027_slice9_evidence_is_indexed_and_non_promoting() -> None:
    source_ref = "docs/rfcs/RFC-0027-slice-9-certified-advise-apis-openapi.md"

    assert source_ref in _read(RFC27_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)

    slice9 = _read(SLICE9_PATH)
    supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    assert "IMPLEMENTED - ADVISE API SURFACE ONLY" in slice9
    assert "No free-form prompt endpoint exists" in slice9
    assert "certified Advise APIs/OpenAPI" in supported
    assert "Gateway publication, Workbench Gateway-first product surface" in supported
    assert "RFC-0028 governs bank-demo/RFP proof through supported claims" in supported


def test_rfc0027_slice9_documents_selected_api_surface_and_boundaries() -> None:
    flat_slice9 = _flat(SLICE9_PATH)

    required = (
        "POST /advisory/copilot/evidence-packets",
        "GET /advisory/copilot/evidence-packets/{evidence_packet_id}",
        "POST /advisory/copilot/actions",
        "GET /advisory/copilot/actions/{run_id}",
        "POST /advisory/copilot/actions/{run_id}/reviews",
        "GET /advisory/copilot/supportability",
        "GET /advisory/proposals/{proposal_id}/versions/{version_id}/copilot-runs",
        "Gateway, Workbench, canonical seed/automation, data-mesh promotion",
        "raw value is not persisted in the run record",
    )
    for item in required:
        assert item in flat_slice9
