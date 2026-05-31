from pathlib import Path

SLICE8_PATH = Path("docs/rfcs/RFC-0024-slice-8-policy-fees-costs-conflicts-and-disclosures.md")


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_rfc0024_slice8_evidence_document_is_indexed_and_scoped() -> None:
    slice8_text = _read(SLICE8_PATH)
    rfc_text = _read("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")

    source_ref = "docs/rfcs/RFC-0024-slice-8-policy-fees-costs-conflicts-and-disclosures.md"
    assert source_ref in rfc_text
    assert source_ref in rfc_index
    assert source_ref in wiki_index
    assert "RFC-0024 Slice 8 is implemented" in wiki_index
    assert "memo-critical policy, fees, costs, conflicts, and disclosure" in wiki_index

    for heading in (
        "## Implemented Behavior",
        "## Design Review",
        "## Acceptance Review",
        "## Current Product Boundary",
        "## Wiki And README Decision",
        "## Remaining Gates",
    ):
        assert heading in slice8_text

    assert "memo_policy_enrichment.py" in slice8_text
    assert "SUITABILITY_AND_BEST_INTEREST" in slice8_text
    assert "FEES_COSTS_TAX_AND_FRICTIONS" in slice8_text
    assert "CONFLICTS_AND_DISCLOSURES" in slice8_text
    assert "AdvisoryProposalMemoEvidencePack:v1" in slice8_text


def test_rfc0024_slice8_supported_features_truth_does_not_overpromote() -> None:
    supported_features = _read("wiki/Supported-Features.md")

    assert "Slice 8 is complete" in supported_features
    assert "memo-critical suitability" in supported_features
    assert "cost/fee/tax/friction limitation" in supported_features
    assert "conflict blocker enrichment" in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1` is active" in supported_features
    assert "client-ready memo publication remains gated" in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1 | Supported" in supported_features
