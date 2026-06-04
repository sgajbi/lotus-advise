from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_rfc0023_slice13_14_closure_hardening_is_indexed() -> None:
    source_ref = "docs/rfcs/RFC-0023-slice-13-14-closure-hardening-and-review.md"
    slice_doc = _read(source_ref)
    main_rfc = _read(
        "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
    )
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")

    assert "Status: Implemented on 2026-05-23" in slice_doc
    assert "not a full client-ready publication capability" in slice_doc
    assert "cannot become `APPROVED_FOR_CLIENT_READY`" in slice_doc
    assert source_ref in main_rfc
    assert source_ref in rfc_index
    assert source_ref in wiki_index


def test_rfc0023_slice13_14_supported_truth_keeps_client_ready_gated() -> None:
    supported = _read("wiki/Supported-Features.md")
    repo_context = _read("REPOSITORY-ENGINEERING-CONTEXT.md")
    narrative_policy_models = _read("src/core/advisory/narrative_policy_models.py")
    narrative_review = _read("src/core/proposals/narrative_review.py")

    assert "Slice 13/14 hardens the closure boundary" in supported
    assert "after Slice 13/14" in supported
    assert "cannot return `APPROVED_FOR_CLIENT_READY`" in repo_context
    assert "keeps client-ready release blocked" in narrative_policy_models
    assert 'return "APPROVED_FOR_CLIENT_READY"' not in narrative_review
    assert "Client-ready proposal commentary | Supported" not in supported
