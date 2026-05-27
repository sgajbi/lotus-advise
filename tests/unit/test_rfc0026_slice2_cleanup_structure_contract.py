from __future__ import annotations

from pathlib import Path

RFC26_PATH = Path("docs/rfcs/RFC-0026-advisor-cockpit-operating-workflow.md")
SLICE2_PATH = Path("docs/rfcs/RFC-0026-slice-2-cleanup-and-structure.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0026_slice2_evidence_is_indexed_and_non_claiming() -> None:
    source_ref = "docs/rfcs/RFC-0026-slice-2-cleanup-and-structure.md"

    assert source_ref in _read(RFC26_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)

    slice2 = _flat(SLICE2_PATH)
    supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    assert "COCKPIT CORE PACKAGE ESTABLISHED" in slice2
    assert "src/core/advisor_cockpit/" in slice2
    assert "No existing proposal, memo, policy, workspace, Gateway, or Workbench behavior" in slice2
    assert "Slice 2 adds the `src/core/advisor_cockpit/` domain package" in supported
    assert "No runtime advisor-cockpit support claim is promoted" in supported


def test_rfc0026_slice2_pins_domain_structure_and_boundaries() -> None:
    slice2 = _flat(SLICE2_PATH)

    required_markers = (
        "src/core/advisor_cockpit/models.py",
        "src/core/advisor_cockpit/vocabulary.py",
        "src/core/advisor_cockpit/pagination.py",
        "default 25, maximum 100",
        "Workbench must receive projected cockpit data rather than infer permissions locally",
        "Unsupported capabilities are explicit model values",
        "no `src.api`, `src.integrations`, or `src.infrastructure` dependency",
        "Deterministic ordering",
    )
    for marker in required_markers:
        assert marker in slice2


def test_rfc0026_slice2_records_next_slice_without_future_deferral() -> None:
    slice2 = _flat(SLICE2_PATH)

    assert "mandatory subsequent RFC-0026 slices" in slice2
    assert "Slice 3 may add data-product posture" in slice2
    assert "Slice 4 can build on the new domain package" in slice2
