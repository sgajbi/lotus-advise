from __future__ import annotations

from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
SLICE6_PATH = Path("docs/rfcs/RFC-0024-slice-6-persistence-replay-idempotency-and-audit.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")


def test_rfc0024_slice6_persistence_evidence_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice6_text = SLICE6_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0024-slice-6-persistence-replay-idempotency-and-audit.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    required_sections = (
        "## Implemented Behavior",
        "## Design Review",
        "## Acceptance Review",
        "## Wiki And README Decision",
        "## Remaining Gates",
    )
    for section in required_sections:
        assert section in slice6_text

    assert "`proposal_memos`" in slice6_text
    assert "ProposalMemoRecord" in slice6_text
    assert "MEMO_IDEMPOTENCY_KEY_CONFLICT" in slice6_text


def test_rfc0024_slice6_keeps_public_memo_support_unpromoted() -> None:
    slice6_text = SLICE6_PATH.read_text(encoding="utf-8")
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")

    assert "does not add memo routes" in slice6_text
    assert "Slices 0-6 are complete" in supported_features
    assert "client-ready memo publication remains gated" in supported_features
    assert "Slice 7 is complete for canonical `lotus-advise` memo" in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1` is active" in supported_features
    assert "Gateway, Workbench, report/render/archive realization" in supported_features
    assert "Advisor proposal memo | Supported" not in supported_features
    assert "Client-ready memo publication | Supported" not in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1 | Supported" in supported_features
