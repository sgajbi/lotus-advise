from pathlib import Path

SLICE10_PATH = Path("docs/rfcs/RFC-0024-slice-10-ai-narrative-and-review-gated-commentary.md")


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_rfc0024_slice10_evidence_document_is_indexed_and_scoped() -> None:
    slice10_text = _read(SLICE10_PATH)
    rfc_text = _read("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")

    source_ref = "docs/rfcs/RFC-0024-slice-10-ai-narrative-and-review-gated-commentary.md"
    assert source_ref in rfc_text
    assert source_ref in rfc_index
    assert source_ref in wiki_index
    assert "RFC-0024 Slice 10 is implemented" in wiki_index
    assert "proposal_memo_commentary.pack@v1" in wiki_index

    for heading in (
        "## Implemented Behavior",
        "## Design Review",
        "## Acceptance Review",
        "## API Boundary",
        "## Wiki And README Decision",
        "## Remaining Gates",
    ):
        assert heading in slice10_text

    assert "src/integrations/lotus_ai/proposal_memo.py" in slice10_text
    assert "MEMO_AI_REFERENCE_RECORDED" in slice10_text
    assert "LOTUS_AI_BASE_URL" in slice10_text


def test_rfc0024_slice10_supported_features_truth_does_not_overpromote() -> None:
    supported_features = _read("wiki/Supported-Features.md")

    assert "Slice 10 is complete" in supported_features
    assert "review-gated advisor-use AI commentary" in supported_features
    assert "deterministic unavailable posture" in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1` is active" in supported_features
    assert "client-ready memo claims remain planned" in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1 | Supported" in supported_features
