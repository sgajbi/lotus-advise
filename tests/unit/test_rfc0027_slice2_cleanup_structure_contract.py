from __future__ import annotations

from pathlib import Path

RFC27_PATH = Path("docs/rfcs/RFC-0027-governed-advisory-ai-copilot.md")
SLICE2_PATH = Path("docs/rfcs/RFC-0027-slice-2-cleanup-and-structure.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0027_slice2_evidence_is_indexed_and_non_claiming() -> None:
    source_ref = "docs/rfcs/RFC-0027-slice-2-cleanup-and-structure.md"

    assert source_ref in _read(RFC27_PATH)
    assert source_ref in _read(RFC_INDEX_PATH)
    assert source_ref in _read(WIKI_RFC_INDEX_PATH)

    slice2 = _read(SLICE2_PATH)
    flat_supported = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    assert "IMPLEMENTED - DOMAIN FOUNDATION ONLY" in slice2
    assert "This slice creates the copilot domain foundation" in slice2
    assert "does not expose copilot APIs" in slice2
    assert "Those remain mandatory subsequent RFC-0027 slices" in slice2
    assert "Implemented for governed internal advisor/reviewer copilot interactions" in (
        flat_supported
    )
    assert "Advise copilot domain foundation" in flat_supported
    assert "Client-ready publication, external client communication" in flat_supported


def test_rfc0027_slice2_records_clean_module_boundaries() -> None:
    flat_slice2 = _flat(SLICE2_PATH)

    required_files = (
        "src/core/advisory_copilot/models.py",
        "src/core/advisory_copilot/catalog.py",
        "src/core/advisory_copilot/evidence_packets.py",
        "src/core/advisory_copilot/guardrails.py",
        "src/core/advisory_copilot/projection.py",
        "src/core/advisory_copilot/review.py",
        "src/core/advisory_copilot/workflow_pack.py",
        "src/core/advisory_copilot/__init__.py",
    )
    for file_path in required_files:
        assert file_path in flat_slice2

    boundaries = (
        "Existing workspace-rationale endpoints and `workspace_rationale.pack@v1` remain separate",
        "RFC-0027 consumes RFC-0023 narrative lineage",
        "RFC-0027 consumes RFC-0024 memo evidence",
        "RFC-0027 consumes RFC-0025 policy evidence",
        "RFC-0027 consumes RFC-0026 cockpit actions",
        "`lotus-ai` remains workflow-pack execution authority",
        "No Gateway or Workbench route is introduced in this slice",
        "client-ready publication is `BLOCKED`",
    )
    for boundary in boundaries:
        assert boundary in flat_slice2


def test_rfc0027_slice2_pins_tests_and_non_leaking_business_copy() -> None:
    flat_slice2 = _flat(SLICE2_PATH)

    assert "tests/unit/advisory/engine/test_engine_advisory_copilot_foundation.py" in flat_slice2
    assert "Verifies the six action families" in flat_slice2
    assert "forbidden-intent reason codes" in flat_slice2
    assert "business-facing projection copy" in flat_slice2
    assert "workflow-pack, provider, prompt, correlation, trace, run ledger, or raw payload" in (
        flat_slice2
    )


def test_rfc0027_slice2_records_dead_code_review_without_removing_supported_paths() -> None:
    flat_slice2 = _flat(SLICE2_PATH)

    assert "No tracked `__pycache__` or `.pyc` files were present" in flat_slice2
    assert "Existing workspace rationale, proposal narrative, proposal memo AI commentary" in (
        flat_slice2
    )
    assert "were not removed or renamed in this slice" in flat_slice2
    assert "`AdvisoryCopilotInteractionRecord:v1` remains unpromoted" in flat_slice2
