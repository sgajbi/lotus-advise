from __future__ import annotations

from pathlib import Path

RFC_PATH = Path(
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)
SLICE11A_PATH = Path(
    "docs/rfcs/RFC-0023-slice-11A-reviewed-narrative-report-request-package-propagation.md"
)
SLICE11BC_PATH = Path(
    "docs/rfcs/RFC-0023-slice-11B-11C-report-render-reviewed-narrative-realization.md"
)
SLICE11D_PATH = Path(
    "docs/rfcs/RFC-0023-slice-11D-archive-reviewed-narrative-artifact-realization.md"
)
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
WIKI_API_SURFACE_PATH = Path("wiki/API-Surface.md")


def test_rfc0023_slice11a_report_request_package_propagation_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice11a_text = SLICE11A_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = (
        "docs/rfcs/RFC-0023-slice-11A-reviewed-narrative-report-request-package-propagation.md"
    )
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Outcome",
        "## Implemented Behavior",
        "## Package Contents",
        "## Blocking Rules",
        "## Remaining Slice 11 Work",
    ):
        assert section in slice11a_text

    assert "include_reviewed_narrative" in slice11a_text
    assert "APPROVED_FOR_ADVISOR_USE" in slice11a_text
    assert "source_narrative_hash" in slice11a_text


def test_rfc0023_slice11a_supported_features_keep_downstream_claims_gated() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "Slices 0-10 complete" in supported_features
    assert "Slice 11A is complete" in supported_features
    assert "Slices 11B/11C are complete" in supported_features
    assert "Slice 11D is complete" in supported_features
    assert "reviewed narrative report-request package propagation" in supported_features
    assert "support-safe reviewed narrative archive metadata summaries" in supported_features
    assert "Gateway/Workbench surfaces" in supported_features
    assert "Client-ready proposal commentary | Supported" not in supported_features


def test_rfc0023_slice11bc_report_render_closure_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice11bc_text = SLICE11BC_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0023-slice-11B-11C-report-render-reviewed-narrative-realization.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Outcome",
        "## Implemented Behavior",
        "## Evidence",
        "## Remaining Slice 11 Work",
    ):
        assert section in slice11bc_text

    assert "lotus-report" in slice11bc_text
    assert "lotus-render" in slice11bc_text
    assert "advisor-use advisory narrative page" in slice11bc_text
    assert "Slice 11D later closed the archive metadata-summary portion" in slice11bc_text
    assert "client-ready" in slice11bc_text
    assert "lotus-report` package consumption" in supported_features
    assert "lotus-render` portfolio-review advisory narrative rendering" in supported_features


def test_rfc0023_slice11d_archive_closure_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice11d_text = SLICE11D_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")
    api_surface = WIKI_API_SURFACE_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0023-slice-11D-archive-reviewed-narrative-artifact-realization.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Outcome",
        "## Implemented Behavior",
        "## Evidence",
        "## Remaining Slice 11 Work",
    ):
        assert section in slice11d_text

    assert "lotus-archive" in slice11d_text
    assert "reviewed_advisory_narrative" in slice11d_text
    assert "APPROVED_FOR_ADVISOR_USE" in slice11d_text
    assert "reviewed_advisory_narrative_archive_summary_preserved" in slice11d_text
    assert "Gateway" in slice11d_text
    assert "client-ready" in slice11d_text
    assert (
        "lotus-archive` support-safe reviewed narrative archive metadata summaries"
        in supported_features
    )
    assert "support-safe archive metadata" in api_surface
