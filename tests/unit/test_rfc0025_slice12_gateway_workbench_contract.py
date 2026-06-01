from pathlib import Path

from tests.unit.capability_source_helpers import read_capability_source

RFC_PATH = Path("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
SLICE12_PATH = Path("docs/rfcs/RFC-0025-slice-12-gateway-workbench-product-realization.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
REPO_CONTEXT_PATH = Path("REPOSITORY-ENGINEERING-CONTEXT.md")
DECLARATION_PATH = Path("contracts/domain-data-products/lotus-advise-products.v1.json")
TELEMETRY_PATH = Path(
    "contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json"
)


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_rfc0025_slice12_gateway_workbench_evidence_is_indexed() -> None:
    source_ref = "docs/rfcs/RFC-0025-slice-12-gateway-workbench-product-realization.md"

    assert source_ref in RFC_PATH.read_text(encoding="utf-8")
    assert source_ref in RFC_INDEX_PATH.read_text(encoding="utf-8")
    assert source_ref in WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")
    assert source_ref in TELEMETRY_PATH.read_text(encoding="utf-8")

    slice_text = SLICE12_PATH.read_text(encoding="utf-8")
    for phrase in (
        "Gateway and Workbench Product Realization",
        "policy-pack and policy-evaluation surface through Gateway",
        "loads policy review queue through Gateway only",
        "loads policy workflow posture through Gateway only",
        "request for more evidence",
        "approval/waiver authority",
        "client-ready publication",
    ):
        assert phrase in slice_text


def test_rfc0025_slice12_updates_supported_boundary_without_product_promotion() -> None:
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8"))
    repo_context = REPO_CONTEXT_PATH.read_text(encoding="utf-8")
    declaration = DECLARATION_PATH.read_text(encoding="utf-8")
    telemetry = TELEMETRY_PATH.read_text(encoding="utf-8")
    capabilities_source = read_capability_source()

    assert (
        "Slice 12 is complete for Gateway and Workbench product realization" in supported_features
    )
    assert "Gateway and Workbench product" in repo_context
    assert "Gateway/Workbench visibility" in declaration
    assert "Gateway routing, Workbench visibility" in telemetry
    assert "RFC-0025-slice-16-final-closure.md" in telemetry
    assert "Gateway/Workbench policy support" not in telemetry
    assert "Gateway/Workbench policy support" not in declaration
    assert "advisory.proposals.policy_evaluation" in capabilities_source
    assert "advisory_policy_evaluation" in capabilities_source
