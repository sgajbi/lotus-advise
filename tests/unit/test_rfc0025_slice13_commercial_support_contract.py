from pathlib import Path

from tests.unit.capability_source_helpers import read_capability_source

SLICE13_PATH = Path("docs/rfcs/RFC-0025-slice-13-commercial-demo-rfp-support.md")
COMMERCIAL_GUIDE_PATH = Path(
    "docs/commercial/RFC-0025-enterprise-policy-pack-commercial-support.md"
)


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_rfc0025_slice13_commercial_material_is_indexed_and_claim_controlled() -> None:
    slice13_text = _read(SLICE13_PATH)
    commercial_text = _read(COMMERCIAL_GUIDE_PATH)
    rfc_text = _read("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")
    demo_readme = _read("docs/demo/README.md")

    source_ref = "docs/rfcs/RFC-0025-slice-13-commercial-demo-rfp-support.md"
    commercial_ref = "docs/commercial/RFC-0025-enterprise-policy-pack-commercial-support.md"
    assert source_ref in rfc_text
    assert source_ref in rfc_index
    assert source_ref in wiki_index
    assert commercial_ref in slice13_text
    assert commercial_ref in rfc_index
    assert commercial_ref in wiki_index
    assert commercial_ref in demo_readme

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


def test_rfc0025_slice13_supported_features_do_not_overclaim() -> None:
    supported_features = _flat(_read("wiki/Supported-Features.md"))
    commercial_text = _read(COMMERCIAL_GUIDE_PATH)
    telemetry_text = _read(
        "contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json"
    )
    declaration_text = _read("contracts/domain-data-products/lotus-advise-products.v1.json")
    capability_text = read_capability_source()

    assert "Slice 13 is complete for policy-pack-specific commercial support material" in (
        supported_features
    )
    assert "active data-product promotion" in supported_features
    assert "client-ready publication" in supported_features
    assert "AdvisoryPolicyEvaluationRecord:v1` is active" in commercial_text
    assert '"completeness_status": "complete"' in telemetry_text
    assert "RFC-0025-slice-13-commercial-demo-rfp-support.md" in telemetry_text
    assert "final closure evidence" in declaration_text
    assert "RFC-0025-slice-16-final-closure.md" in telemetry_text
    assert "advisory.proposals.policy_evaluation" in capability_text
    assert "advisory_policy_evaluation" in capability_text
