from pathlib import Path

SLICE7_PATH = Path("docs/rfcs/RFC-0024-slice-7-certified-apis-and-openapi.md")


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_rfc0024_slice7_evidence_document_is_indexed_and_scoped() -> None:
    slice7_text = _read(SLICE7_PATH)
    rfc_text = _read("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")

    source_ref = "docs/rfcs/RFC-0024-slice-7-certified-apis-and-openapi.md"
    assert source_ref in rfc_text
    assert source_ref in rfc_index
    assert "RFC-0024 Slice 7 is implemented" in wiki_index
    assert "certified Advise memo APIs and OpenAPI" in wiki_index

    for heading in (
        "## Implemented Behavior",
        "## Design Review",
        "## Acceptance Review",
        "## API Boundary",
        "## Wiki And README Decision",
        "## Remaining Gates",
    ):
        assert heading in slice7_text

    assert "/advisory/proposals/{proposal_id}/versions/{version_no}/memo" in slice7_text
    assert "ProposalMemoResponse" in slice7_text
    assert "ProposalMemoReplayEvidenceResponse" in slice7_text
    assert "Gateway routes, Workbench" in slice7_text
    assert "client-ready memo" in slice7_text


def test_rfc0024_slice7_supported_features_truth_does_not_overpromote() -> None:
    supported_features = _read("wiki/Supported-Features.md")

    assert "Slice 7 is complete" in supported_features
    assert "canonical `lotus-advise` memo create/read/projection/review" in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1` is active" in supported_features
    assert "Gateway, Workbench, report/render/archive realization" in supported_features
    assert "client-ready memo publication remains gated" in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1 | Supported" in supported_features
