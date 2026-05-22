from __future__ import annotations

from pathlib import Path

RFC_PATH = Path(
    "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
)
SLICE11A_PATH = Path(
    "docs/rfcs/RFC-0023-slice-11A-reviewed-narrative-report-request-package-propagation.md"
)
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


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
    assert "Slice 11A is also complete" in supported_features
    assert "reviewed narrative report-request package propagation" in supported_features
    assert "concrete report/render/archive artifact realization" in supported_features
    assert "Gateway/Workbench surfaces" in supported_features
    assert "Client-ready proposal commentary | Supported" not in supported_features
