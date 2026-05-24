from pathlib import Path

SLICE11_PATH = Path("docs/rfcs/RFC-0024-slice-11-gateway-workbench-product-realization.md")


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_rfc0024_slice11_evidence_document_is_indexed_and_scoped() -> None:
    slice11_text = _read(SLICE11_PATH)
    rfc_text = _read("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")

    source_ref = "docs/rfcs/RFC-0024-slice-11-gateway-workbench-product-realization.md"
    assert source_ref in rfc_text
    assert source_ref in rfc_index
    assert source_ref in wiki_index
    assert "RFC-0024 Slice 11 is implemented" in wiki_index
    assert "Gateway/BFF memo APIs" in slice11_text

    for heading in (
        "## Implemented Behavior",
        "## Gateway Boundary",
        "## Workbench Boundary",
        "## Acceptance Review",
        "## Wiki And README Decision",
        "## Remaining Gates",
    ):
        assert heading in slice11_text

    assert "../lotus-gateway/src/app/routers/proposals.py" in slice11_text
    assert "../lotus-workbench/tests/e2e/proposal-memo-posture.spec.ts" in slice11_text
    assert "npx playwright test tests/e2e/proposal-memo-posture.spec.ts" in slice11_text


def test_rfc0024_slice11_supported_features_truth_does_not_overpromote() -> None:
    supported_features = _read("wiki/Supported-Features.md")
    repo_context = _read("REPOSITORY-ENGINEERING-CONTEXT.md")

    assert "Slice 11 is complete" in supported_features
    assert "Gateway and Workbench product realization" in supported_features
    assert "no client-ready controls" in supported_features
    assert "`AdvisoryProposalMemoEvidencePack:v1` remains unpromoted" in supported_features
    assert (
        "Active data-product support, commercial/demo claims, and client-ready memo claims "
        "remain planned"
    ) in supported_features
    assert "Gateway now routes canonical Advise memo endpoints" in repo_context
    assert "without local memo inference" in repo_context
    assert "AdvisoryProposalMemoEvidencePack:v1 | Supported" not in supported_features
