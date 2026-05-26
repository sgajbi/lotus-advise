from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
SLICE8_PATH = Path("docs/rfcs/RFC-0025-slice-8-certified-apis-and-openapi.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
ROUTE_SOURCE_PATH = Path("src/api/proposals/routes_policy_evaluations.py")
PERSISTENCE_SOURCE_PATH = Path("src/core/policy_packs/persistence.py")
SUPPORTABILITY_SOURCE_PATH = Path("src/core/policy_packs/supportability.py")
DECLARATION_PATH = Path("contracts/domain-data-products/lotus-advise-products.v1.json")
TELEMETRY_PATH = Path(
    "contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json"
)
CAPABILITIES_SOURCE_PATH = Path("src/api/capabilities/service.py")


def test_rfc0025_slice8_certified_api_evidence_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice8_text = SLICE8_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0025-slice-8-certified-apis-and-openapi.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Scope Boundary",
        "## Implementation",
        "## Data Product Posture",
        "## Acceptance Evidence",
        "## Wiki And README Decision",
    ):
        assert section in slice8_text

    assert "IMPLEMENTED - CERTIFIED ADVISE API SURFACE ONLY" in slice8_text
    assert "not yet consumable through Gateway/Workbench" in slice8_text


def test_rfc0025_slice8_exposes_advise_routes_without_capability_promotion() -> None:
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")
    routes_source = ROUTE_SOURCE_PATH.read_text(encoding="utf-8")
    supportability_source = SUPPORTABILITY_SOURCE_PATH.read_text(encoding="utf-8")
    declaration_source = DECLARATION_PATH.read_text(encoding="utf-8")
    telemetry_source = TELEMETRY_PATH.read_text(encoding="utf-8")
    capabilities_source = CAPABILITIES_SOURCE_PATH.read_text(encoding="utf-8")

    assert "Advisory Policy Evaluation" in routes_source
    assert "/advisory/policy-evaluations/review-queue" in routes_source
    assert "/advisory/policy-evaluations/{evaluation_id}/sign-off-package" in routes_source
    assert "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API" in supportability_source
    assert "/advisory/policy-evaluations/{evaluation_id}/lineage" in declaration_source
    assert "RFC-0025-slice-8-certified-apis-and-openapi.md" in telemetry_source
    assert "certified Advise evaluation APIs" in supported_features
    assert (
        "Slice 12 is complete for Gateway and Workbench product realization" in supported_features
    )
    assert "active data-product promotion" in supported_features
    assert "advisory.proposals.policy_evaluation" not in capabilities_source
    assert "advisory_policy_evaluation" not in capabilities_source
