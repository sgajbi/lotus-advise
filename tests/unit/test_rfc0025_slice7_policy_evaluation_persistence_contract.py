from pathlib import Path

RFC_PATH = Path("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
SLICE7_PATH = Path("docs/rfcs/RFC-0025-slice-7-policy-evaluation-persistence-replay-audit.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
PERSISTENCE_SOURCE_PATH = Path("src/core/policy_packs/persistence.py")
EVALUATION_SOURCE_PATH = Path("src/core/policy_packs/evaluation.py")
MODELS_SOURCE_PATH = Path("src/core/policy_packs/models.py")
SUPPORTABILITY_SOURCE_PATH = Path("src/core/policy_packs/supportability.py")


def test_rfc0025_slice7_policy_evaluation_persistence_evidence_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice7_text = SLICE7_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0025-slice-7-policy-evaluation-persistence-replay-audit.md"
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
        assert section in slice7_text

    assert "IMPLEMENTED - INTERNAL PERSISTENCE AND REPLAY ONLY" in slice7_text
    assert "`rfc0025.policy-evaluation-persistence.v1`" in slice7_text
    assert "This slice does not implement certified policy evaluation APIs" in slice7_text


def test_rfc0025_slice7_keeps_api_product_surface_and_client_ready_gated() -> None:
    slice7_text = SLICE7_PATH.read_text(encoding="utf-8")
    supported_features = WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8")
    persistence_source = PERSISTENCE_SOURCE_PATH.read_text(encoding="utf-8")
    supportability_source = SUPPORTABILITY_SOURCE_PATH.read_text(encoding="utf-8")
    models_source = MODELS_SOURCE_PATH.read_text(encoding="utf-8")

    assert "POLICY_EVALUATION_PERSISTENCE_CONTRACT_VERSION" in persistence_source
    assert "rfc0025.policy-evaluation-persistence.v1" in supportability_source
    assert "PolicyEvaluationRecordStore" in persistence_source
    assert "POLICY_EVALUATION_IDEMPOTENCY_KEY_CONFLICT" in persistence_source
    assert "PIN_POLICY_VERSION_AND_COMPARE_SOURCE_HASHES" in persistence_source
    assert "PolicyEvaluationRecord" in models_source
    assert "PolicyEvaluationReplayResponse" in models_source
    assert '"policy_evaluation_api": "SUPPORTED_BY_RFC0025_SLICE8_ADVISE_API"' in (
        supportability_source
    )
    assert '"gateway_supported": True' in supportability_source
    assert '"gateway_support": "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_BFF"' in supportability_source
    assert '"workbench_supported": True' in supportability_source
    assert '"workbench_support": "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_ONLY_UI"' in (
        supportability_source
    )
    assert '"active_data_product_promotion": "SUPPORTED_BY_RFC0025_SLICE16_FINAL_CLOSURE"' in (
        supportability_source
    )
    assert "active governed policy evidence data product" in supported_features
    assert "client-ready publication" in supported_features
    assert "RFC-0025 is implemented for advisor/compliance policy evidence through Slice 16" in (
        supported_features
    )
    assert "current trust telemetry" in supported_features
    assert "no api or product surface promoted" in slice7_text.lower()
