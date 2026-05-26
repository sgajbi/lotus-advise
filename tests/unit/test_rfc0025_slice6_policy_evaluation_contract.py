from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
SLICE6_PATH = Path("docs/rfcs/RFC-0025-slice-6-policy-applicability-and-evaluation-engine.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
EVALUATION_SOURCE_PATH = Path("src/core/policy_packs/evaluation.py")
MODELS_SOURCE_PATH = Path("src/core/policy_packs/models.py")
READINESS_SOURCE_PATH = Path("src/core/proposals/policy_source_readiness.py")


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
    evaluation_source = EVALUATION_SOURCE_PATH.read_text(encoding="utf-8")
    models_source = MODELS_SOURCE_PATH.read_text(encoding="utf-8")
    readiness_source = READINESS_SOURCE_PATH.read_text(encoding="utf-8")

    assert "rfc0025.policy-evaluation-engine.v1" in evaluation_source
    assert "POLICY_PACK_VERSION_NOT_ACTIVE_FOR_EVALUATION" in evaluation_source
    assert "policy_evaluation_persistence" in evaluation_source
    assert '"policy_evaluation_api": "NOT_IMPLEMENTED"' in evaluation_source
    assert '"gateway_supported": False' in evaluation_source
    assert '"workbench_supported": False' in evaluation_source
    assert "PolicyRuleEvaluationResult" in models_source
    assert "source_authority_refs" in models_source
    assert "SOURCE_READINESS_WITH_INTERNAL_POLICY_EVALUATION_ENGINE" in readiness_source
    assert "INTERNAL_ENGINE_ONLY_NO_PERSISTED_API" in readiness_source
    assert "proposal policy evaluation persistence" in supported_features
    assert "certified evaluation APIs" in supported_features
    assert "remain gated" in supported_features
    assert "no persistence/API/product-surface promotion" in slice6_text
