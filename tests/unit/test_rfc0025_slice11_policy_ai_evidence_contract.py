from pathlib import Path

from tests.unit.capability_source_helpers import read_capability_source

RFC_PATH = Path("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
SLICE11_PATH = Path("docs/rfcs/RFC-0025-slice-11-ai-policy-evidence-boundary.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
ROUTE_SOURCE_PATH = Path("src/api/proposals/routes_policy_evaluations.py")
AI_SOURCE_PATH = Path("src/core/policy_packs/ai.py")
AI_MODELS_SOURCE_PATH = Path("src/core/policy_packs/ai_models.py")
AI_ADAPTER_SOURCE_PATH = Path("src/integrations/lotus_ai/policy_evidence.py")
MODELS_SOURCE_PATH = Path("src/core/policy_packs/models.py")
DECLARATION_PATH = Path("contracts/domain-data-products/lotus-advise-products.v1.json")
TELEMETRY_PATH = Path(
    "contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json"
)


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_rfc0025_slice11_policy_ai_evidence_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice11_text = SLICE11_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0025-slice-11-ai-policy-evidence-boundary.md"
    assert source_ref in rfc_text
    assert source_ref in index_text
    assert source_ref in wiki_index_text

    for section in (
        "## Scope Boundary",
        "## Implementation",
        "## Guardrails",
        "## Data Product Posture",
        "## Acceptance Evidence",
        "## Wiki And README Decision",
    ):
        assert section in slice11_text

    assert "IMPLEMENTED - ADVISE AI EVIDENCE BOUNDARY ONLY" in slice11_text
    assert "AI output cannot change policy status" in slice11_text
    assert "Gateway/Workbench policy consumption" in slice11_text


def test_rfc0025_slice11_records_ai_lineage_without_product_surface_promotion() -> None:
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8"))
    routes_source = ROUTE_SOURCE_PATH.read_text(encoding="utf-8")
    ai_source = AI_SOURCE_PATH.read_text(encoding="utf-8")
    ai_models_source = AI_MODELS_SOURCE_PATH.read_text(encoding="utf-8")
    adapter_source = AI_ADAPTER_SOURCE_PATH.read_text(encoding="utf-8")
    compatibility_models_source = MODELS_SOURCE_PATH.read_text(encoding="utf-8")
    declaration_source = DECLARATION_PATH.read_text(encoding="utf-8")
    telemetry_source = TELEMETRY_PATH.read_text(encoding="utf-8")
    capabilities_source = read_capability_source()

    assert "/advisory/policy-evaluations/{evaluation_id}/ai-evidence" in routes_source
    assert "PolicyEvaluationAiEvidenceRequest" in ai_models_source
    assert "PolicyEvaluationAiEvidenceResponse" in ai_models_source
    assert "PolicyEvaluationAiEvidenceRequest" in compatibility_models_source
    assert "PolicyEvaluationAiEvidenceResponse" in compatibility_models_source
    assert "rfc0025.policy-ai-evidence-boundary.v1" in ai_source
    assert "POLICY_EVALUATION_AI_EVIDENCE_RECORDED" in ai_source
    assert "POLICY_AI_EVIDENCE_FORBIDDEN_ACTION" in ai_source
    assert "raw_source_evidence_included" in ai_source
    assert "policy_evidence_summary.pack" in adapter_source
    assert "EXPLANATION_ONLY" in adapter_source
    assert "/advisory/policy-evaluations/{evaluation_id}/ai-evidence" in declaration_source
    assert "RFC-0025-slice-11-ai-policy-evidence-boundary.md" in telemetry_source
    assert "src/core/policy_packs/ai.py" in telemetry_source
    assert "src/integrations/lotus_ai/policy_evidence.py" in telemetry_source
    assert "AI policy-evidence consumption" in supported_features
    assert "redacted bounded evidence" in supported_features
    assert "forbidden actions are rejected" in supported_features
    assert "AI output is non-authoritative for policy status" in supported_features
    assert (
        "Slice 12 is complete for Gateway and Workbench product realization" in supported_features
    )
    assert "active data-product promotion" in supported_features
    assert "client-ready publication" in supported_features
    assert "advisory.proposals.policy_evaluation" in capabilities_source
    assert "advisory_policy_evaluation" in capabilities_source
