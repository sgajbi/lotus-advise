from __future__ import annotations

from pathlib import Path

SLICE17_PATH = Path("docs/rfcs/RFC-0025-slice-17-post-completion-communication.md")


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_rfc0025_slice17_communication_is_indexed() -> None:
    rfc_text = _read("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")

    source_ref = "docs/rfcs/RFC-0025-slice-17-post-completion-communication.md"

    assert SLICE17_PATH.exists()
    assert source_ref in rfc_text
    assert source_ref in rfc_index
    assert source_ref in wiki_index
    assert "RFC-0025 Slice 17 is implemented as post-completion communication" in wiki_index


def test_rfc0025_slice17_records_platform_draft_and_ledger_update() -> None:
    slice_text = _read(SLICE17_PATH)

    draft_name = "LI-2026-05-26-042-policy-evidence-should-show-its-limits.md"
    required_terms = [
        draft_name,
        "thought-leadership/linkedin/drafts/",
        "content-ledger.md",
        "lotus-linkedin-thought-leadership",
        "does not mention Lotus",
        "completed approval, waiver, sign-off authority, client-ready publication",
        "draft remains in `draft` status",
    ]
    for term in required_terms:
        assert term in slice_text


def test_rfc0025_slice17_draft_preserves_public_claim_boundaries() -> None:
    slice_text = _read(SLICE17_PATH)

    forbidden_claims = [
        "bank uses",
        "client-ready publication is supported",
        "external client communication is supported",
        "approved for client",
    ]
    for claim in forbidden_claims:
        assert claim not in slice_text

    required_boundary_terms = [
        "does not mention Lotus",
        "investment advice",
        "regulatory advice",
        "AI claims",
        "bank adoption",
        "explicit separation from completed approval, waiver, sign-off authority",
    ]
    for term in required_boundary_terms:
        assert term in slice_text
