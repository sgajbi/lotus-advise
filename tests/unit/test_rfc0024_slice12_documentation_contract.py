from pathlib import Path

SLICE12_PATH = Path("docs/rfcs/RFC-0024-slice-12-commercial-demo-rfp-support.md")
COMMERCIAL_GUIDE_PATH = Path("docs/commercial/RFC-0024-advisor-proposal-memo-commercial-support.md")


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_rfc0024_slice12_commercial_material_is_indexed_and_claim_controlled() -> None:
    slice12_text = _read(SLICE12_PATH)
    commercial_text = _read(COMMERCIAL_GUIDE_PATH)
    rfc_text = _read("docs/rfcs/RFC-0024-advisor-proposal-memo-and-evidence-pack.md")
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")

    source_ref = "docs/rfcs/RFC-0024-slice-12-commercial-demo-rfp-support.md"
    commercial_ref = "docs/commercial/RFC-0024-advisor-proposal-memo-commercial-support.md"
    assert source_ref in rfc_text
    assert source_ref in rfc_index
    assert source_ref in wiki_index
    assert commercial_ref in slice12_text
    assert commercial_ref in rfc_index
    assert commercial_ref in wiki_index

    for heading in (
        "## Claim Register",
        "## Demo Notes",
        "## API Examples",
        "## Architecture Flow",
        "## Operator Guidance",
        "## Security And RFP-Safe Wording",
        "## RFC-0028 Boundary",
    ):
        assert heading in commercial_text

    assert "Safe RFP wording" in commercial_text
    assert "Unsafe wording" in commercial_text
    assert "No RFC-0028 source update is required" in commercial_text
    assert "Do not label screenshots or outputs as demo-ready for clients" in commercial_text


def test_rfc0024_slice12_supported_features_do_not_overclaim() -> None:
    supported_features = _read("wiki/Supported-Features.md")
    commercial_text = _read(COMMERCIAL_GUIDE_PATH)
    telemetry_text = _read(
        "contracts/trust-telemetry/advisory-proposal-memo-evidence-pack.telemetry.v1.json"
    )

    assert "Slice 12 is complete for memo-specific commercial" in supported_features
    assert "full bank-demo/RFP claims" in supported_features
    assert "client-ready memo claims remain planned" in supported_features
    assert "`AdvisoryProposalMemoEvidencePack:v1` remains unpromoted" in supported_features
    assert "AdvisoryProposalMemoEvidencePack:v1 | Supported" not in supported_features
    assert "client-ready memo publication" in commercial_text
    assert '"completeness_status": "blocked"' in telemetry_text
    assert "active data-product promotion" in telemetry_text
