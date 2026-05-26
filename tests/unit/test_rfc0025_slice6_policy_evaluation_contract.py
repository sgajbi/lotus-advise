from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
SLICE6_PATH = Path("docs/rfcs/RFC-0025-slice-6-policy-applicability-and-evaluation-engine.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
EVALUATION_SOURCE_PATH = Path("src/core/policy_packs/evaluation.py")
MODELS_SOURCE_PATH = Path("src/core/policy_packs/models.py")
READINESS_SOURCE_PATH = Path("src/core/proposals/policy_source_readiness.py")
SUPPORTABILITY_SOURCE_PATH = Path("src/core/policy_packs/supportability.py")


def test_rfc0025_slice6_policy_evaluation_evidence_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice6_text = SLICE6_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0025-slice-6-policy-applicability-and-evaluation-engine.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Scope Boundary",
        "## Implementation",
        "## Source-Readiness Update",
        "## Acceptance Evidence",
        "## Wiki And README Decision",
    ):
        assert section in slice6_text

    assert "IMPLEMENTED - INTERNAL EVALUATION ENGINE ONLY" in slice6_text
    assert "`rfc0025.policy-evaluation-engine.v1`" in slice6_text
    assert "This slice does not implement persisted policy evaluation records" in slice6_text


def test_rfc0025_slice6_keeps_product_surface_and_persistence_gated() -> None:
    slice6_text = SLICE6_PATH.read_text(encoding="utf-8")
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")
    supportability_source = SUPPORTABILITY_SOURCE_PATH.read_text(encoding="utf-8")
    models_source = MODELS_SOURCE_PATH.read_text(encoding="utf-8")
    readiness_source = READINESS_SOURCE_PATH.read_text(encoding="utf-8")

    assert "rfc0025.policy-evaluation-engine.v1" in supportability_source
    assert "POLICY_PACK_VERSION_NOT_ACTIVE_FOR_EVALUATION" in EVALUATION_SOURCE_PATH.read_text(
        encoding="utf-8"
    )
    assert "policy_evaluation_persistence" in supportability_source
    assert '"policy_evaluation_api": "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API"' in (
        supportability_source
    )
    assert '"gateway_supported": True' in supportability_source
    assert '"gateway_support": "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_BFF"' in supportability_source
    assert '"workbench_supported": True' in supportability_source
    assert '"workbench_support": "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_ONLY_UI"' in (
        supportability_source
    )
    assert '"active_data_product_promotion": "BLOCKED_UNTIL_FINAL_CLOSURE"' in (
        supportability_source
    )
    assert "PolicyRuleEvaluationResult" in models_source
    assert "source_authority_refs" in models_source
    assert "SOURCE_READINESS_WITH_INTERNAL_POLICY_EVALUATION_ENGINE" in readiness_source
    assert "INTERNAL_ENGINE_ONLY_NO_PERSISTED_API" in readiness_source
    assert "certified APIs" in supported_features
    assert "Implementation in progress through Slice 15" in supported_features
    assert "remain gated" in supported_features
    assert "no persistence/API/product-surface promotion" in slice6_text
