from pathlib import Path

SLICE16_PATH = Path("docs/rfcs/RFC-0024-slice-16-final-closure.md")


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_rfc0024_slice16_closure_is_indexed() -> None:
    rfc_text = _read("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")

    source_ref = "docs/rfcs/RFC-0024-slice-16-final-closure.md"

    assert SLICE16_PATH.exists()
    assert source_ref in rfc_text
    assert source_ref in rfc_index
    assert source_ref in wiki_index
    assert "RFC-0024 Slice 16 is implemented as final closure" in wiki_index


def test_rfc0024_slice16_closes_advisor_use_without_client_ready_claims() -> None:
    slice_text = _read(SLICE16_PATH)
    supported_features = _read("wiki/Supported-Features.md")
    repo_context = _read("REPOSITORY-ENGINEERING-CONTEXT.md")

    required_terms = [
        "RFC-0024 is implemented for the supported advisor-use proposal memo",
        "client-ready memo publication is not supported",
        "external client communication is not supported",
        "full RFC-0028 bank-demo/RFP package claims remain gated",
        "No Lotus agent context, skill, or procedural guidance change is required",
    ]
    for term in required_terms:
        assert term in slice_text

    assert "RFC-0024 is implemented for advisor-use proposal memo evidence" in supported_features
    assert "client-ready memo publication remains gated" in supported_features
    assert "RFC-0024 is closed for advisor-use memo evidence" in repo_context


def test_rfc0024_slice16_updates_trust_and_product_closure_truth() -> None:
    telemetry_text = _read(
        "contracts/trust-telemetry/advisory-proposal-memo-evidence-pack.telemetry.v1.json"
    )
    declaration_text = _read("contracts/domain-data-products/lotus-advise-products.v1.json")

    assert "RFC-0024-slice-15-final-hardening-and-review.md" in telemetry_text
    assert "RFC-0024-slice-16-final-closure.md" in telemetry_text
    assert "RFC-0024 final closure" in telemetry_text
    assert "canonical Workbench proof" in declaration_text
    assert "client-ready memo publication and external client communication remain blocked" in (
        declaration_text
    )


def test_rfc0024_closure_resolves_slice0_questions_with_answers() -> None:
    rfc_text = _read("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")

    assert "Remaining unsupported boundaries after Slice 17" in rfc_text
    assert "LinkedIn post-completion drafting remains a later communication slice" not in rfc_text
    assert "| Question | Closure answer |" in rfc_text
    assert "RFC-0024 supports advisor-use memo evidence only" in rfc_text
    assert "Slice 8 implemented the memo-critical subset" in rfc_text
    assert "Canonical proof uses `PB_SG_GLOBAL_BAL_001`" in rfc_text
