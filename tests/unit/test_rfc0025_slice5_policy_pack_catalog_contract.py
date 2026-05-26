from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
SLICE5_PATH = Path("docs/rfcs/RFC-0025-slice-5-policy-pack-catalog-schema-activation.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
CATALOG_SOURCE_PATH = Path("src/core/policy_packs/catalog.py")
SUPPORTABILITY_SOURCE_PATH = Path("src/core/policy_packs/supportability.py")
ROUTE_SOURCE_PATH = Path("src/api/proposals/routes_policy_packs.py")
CAPABILITIES_SOURCE_PATH = Path("src/api/capabilities/service.py")


def test_rfc0025_slice5_policy_pack_catalog_evidence_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice5_text = SLICE5_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0025-slice-5-policy-pack-catalog-schema-activation.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    required_sections = (
        "## Scope Boundary",
        "## Implementation",
        "## Acceptance Evidence",
        "## Wiki And README Decision",
    )
    for section in required_sections:
        assert section in slice5_text

    assert "IMPLEMENTED - CATALOG AND ACTIVATION ONLY" in slice5_text
    assert "`GLOBAL_PRIVATE_BANKING_BASELINE`" in slice5_text
    assert "`SG_PRIVATE_BANKING_REFERENCE`" in slice5_text
    assert "`REFERENCE_EXAMPLE_NOT_LEGAL_ADVICE`" in slice5_text


def test_rfc0025_slice5_promotes_catalog_without_policy_evaluation_claims() -> None:
    slice5_text = SLICE5_PATH.read_text(encoding="utf-8")
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")
    catalog_source = CATALOG_SOURCE_PATH.read_text(encoding="utf-8")
    supportability_source = SUPPORTABILITY_SOURCE_PATH.read_text(encoding="utf-8")
    route_source = ROUTE_SOURCE_PATH.read_text(encoding="utf-8")
    capabilities_source = CAPABILITIES_SOURCE_PATH.read_text(encoding="utf-8")

    assert "rfc0025.policy-pack-catalog.v1" in supportability_source
    assert "POLICY_PACK_MAKER_CHECKER_REQUIRES_DIFFERENT_ACTOR" in catalog_source
    assert "POLICY_PACK_VERSION_ALREADY_ACTIVE_IMMUTABLE" in catalog_source
    assert '"policy_evaluation": "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API"' in supportability_source
    assert "/advisory/policy-packs" in route_source
    assert "advisory.policy_pack_catalog" in capabilities_source
    assert "advisory.proposals.policy_evaluation" in capabilities_source
    assert "certified Advise evaluation APIs" in supported_features
    assert "remain gated" in supported_features
    assert "This slice does not implement proposal policy evaluation" in slice5_text
