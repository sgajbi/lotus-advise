from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_rfc0023_slice12_live_and_canonical_proof_is_indexed() -> None:
    slice_doc = _read(
        "docs/rfcs/RFC-0023-slice-12-live-validation-canonical-proof-and-operator-evidence.md"
    )
    main_rfc = _read(
        "docs/rfcs/RFC-0023-grounded-advisory-ai-narrative-and-client-ready-proposal-commentary.md"
    )
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")

    source_ref = (
        "docs/rfcs/RFC-0023-slice-12-live-validation-canonical-proof-and-operator-evidence.md"
    )
    assert "Status: Implemented on 2026-05-22" in slice_doc
    assert "stateful_input.narrative_request" in slice_doc
    assert "proposal.narrative_posture" in slice_doc
    assert "LOTUS_ADVISE_VALIDATE_AI_ASSISTED_NARRATIVE=1" in slice_doc
    assert "client-ready publication" in slice_doc
    assert source_ref in main_rfc
    assert "Slice 12 live/canonical proof closure" in rfc_index
    assert source_ref in wiki_index


def test_rfc0023_slice12_supported_features_do_not_promote_client_ready() -> None:
    supported = _read("wiki/Supported-Features.md")
    api_surface = _read("wiki/API-Surface.md")
    repo_context = _read("REPOSITORY-ENGINEERING-CONTEXT.md")
    readme = _read("README.md")

    assert "stateful `stateful_input.narrative_request`" in supported
    assert "governed canonical Workbench proof" in supported
    assert "external client communication remain gated" in supported
    assert (
        "Creates governed advisor-review, compliance-review, and client-ready proposal narrative"
        not in supported
    )
    assert (
        "Implements governed advisor-review proposal narrative evidence from deterministic "
        "proposal facts"
    ) in supported
    assert "not supported RFC-0023 closure claims" in _read("wiki/RFC-Index.md")
    assert "governed `proposal.narrative_posture` panel proof" in api_surface
    assert "proof now covers `proposal.narrative_posture`" in repo_context
    assert "governed Workbench canonical proof" in readme
