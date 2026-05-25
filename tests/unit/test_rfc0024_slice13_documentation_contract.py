from pathlib import Path

SLICE13_PATH = Path("docs/rfcs/RFC-0024-slice-13-implementation-proof.md")


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_rfc0024_slice13_live_proof_is_indexed() -> None:
    rfc_text = _read("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")

    source_ref = "docs/rfcs/RFC-0024-slice-13-implementation-proof.md"

    assert SLICE13_PATH.exists()
    assert source_ref in rfc_text
    assert source_ref in rfc_index
    assert source_ref in wiki_index
    assert "RFC-0024 Slice 13 is implemented" in wiki_index


def test_rfc0024_slice13_pins_live_suite_memo_proof_without_client_ready_promotion() -> None:
    slice_text = _read(SLICE13_PATH)
    supported_features = _read("wiki/Supported-Features.md")
    repo_context = _read("REPOSITORY-ENGINEERING-CONTEXT.md")

    required_terms = [
        "proposal_memo",
        "create/read/projection/review/report-package/AI-commentary/lineage/replay",
        "stateful source dependency path",
        "client-ready memo-review rejection",
        "client-ready report-document rejection",
        "authoritative_for_memo_status=false",
        "replay evidence with exact memo hash",
    ]
    for term in required_terms:
        assert term in slice_text

    assert "Slice 13 is complete for memo implementation proof" in supported_features
    assert "live-suite implementation proof" in repo_context
    assert "client-ready memo claims remain planned" in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1 | Supported" in supported_features


def test_rfc0024_slice13_trust_telemetry_blocks_only_remaining_product_promotion() -> None:
    telemetry_text = _read(
        "contracts/trust-telemetry/advisory-proposal-memo-evidence-pack.telemetry.v1.json"
    )
    declaration_text = _read("contracts/domain-data-products/lotus-advise-products.v1.json")

    assert "RFC-0024-slice-13-implementation-proof.md" in telemetry_text
    assert "live-suite-implementation-proof" in telemetry_text
    assert "full implementation proof" not in telemetry_text
    assert "RFC-0024-slice-14-data-product-promotion-and-supportability-hardening.md" in (
        telemetry_text
    )
    assert "client-ready memo publication" in telemetry_text
    assert "live-suite implementation proof" in declaration_text
    assert "active product is bounded to advisor-use memo evidence" in declaration_text
