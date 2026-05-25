from pathlib import Path

SLICE17_PATH = Path("docs/rfcs/RFC-0024-slice-17-post-completion-communication.md")


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_rfc0024_slice17_communication_is_indexed() -> None:
    rfc_text = _read("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")

    source_ref = "docs/rfcs/RFC-0024-slice-17-post-completion-communication.md"

    assert SLICE17_PATH.exists()
    assert source_ref in rfc_text
    assert source_ref in rfc_index
    assert source_ref in wiki_index
    assert "RFC-0024 Slice 17 is implemented as post-completion communication" in wiki_index


def test_rfc0024_slice17_records_platform_draft_without_product_overclaim() -> None:
    slice_text = _read(SLICE17_PATH)
    rfc_text = _read("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")

    required_terms = [
        "LI-2026-05-25-036-a-proposal-memo-is-an-evidence-product.md",
        "content-ledger.md",
        "lotus-platform` PR #357",
        "2e0f0aa6dc2eee9e4c9cf9dc415d20595b77a990",
        "does not mention Lotus",
        "does not claim client-ready memo publication",
        "draft remains in `draft` status",
    ]
    for term in required_terms:
        assert term in slice_text

    assert "Slice 17 post-completion communication" in rfc_text
    assert "client-ready memo publication remains gated" in rfc_text
