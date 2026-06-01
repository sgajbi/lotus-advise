from pathlib import Path

from tests.unit.capability_source_helpers import read_capability_source

RFC_PATH = Path("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
SLICE9_PATH = Path("docs/rfcs/RFC-0025-slice-9-policy-approval-consent-signoff-workflow.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
ROUTE_SOURCE_PATH = Path("src/api/proposals/routes_policy_evaluations.py")
WORKFLOW_SOURCE_PATH = Path("src/core/policy_packs/workflow.py")
SUPPORTABILITY_SOURCE_PATH = Path("src/core/policy_packs/supportability.py")
MODELS_SOURCE_PATH = Path("src/core/policy_packs/models.py")
WORKFLOW_MODELS_SOURCE_PATH = Path("src/core/policy_packs/workflow_models.py")
DECLARATION_PATH = Path("contracts/domain-data-products/lotus-advise-products.v1.json")
TELEMETRY_PATH = Path(
    "contracts/trust-telemetry/advisory-policy-evaluation-record.telemetry.v1.json"
)


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_rfc0025_slice9_policy_workflow_evidence_is_indexed() -> None:
    rfc_text = RFC_PATH.read_text(encoding="utf-8")
    slice9_text = SLICE9_PATH.read_text(encoding="utf-8")
    index_text = RFC_INDEX_PATH.read_text(encoding="utf-8")
    wiki_index_text = WIKI_RFC_INDEX_PATH.read_text(encoding="utf-8")

    source_ref = "docs/rfcs/RFC-0025-slice-9-policy-approval-consent-signoff-workflow.md"
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
        assert section in slice9_text

    assert "IMPLEMENTED - ADVISE SOURCE WORKFLOW ONLY" in slice9_text
    assert "report/render/archive realization" in slice9_text
    assert "client-ready publication" in slice9_text


def test_rfc0025_slice9_exposes_workflow_without_product_surface_promotion() -> None:
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH.read_text(encoding="utf-8"))
    routes_source = ROUTE_SOURCE_PATH.read_text(encoding="utf-8")
    workflow_source = WORKFLOW_SOURCE_PATH.read_text(encoding="utf-8")
    workflow_models_source = WORKFLOW_MODELS_SOURCE_PATH.read_text(encoding="utf-8")
    supportability_source = SUPPORTABILITY_SOURCE_PATH.read_text(encoding="utf-8")
    compatibility_models_source = MODELS_SOURCE_PATH.read_text(encoding="utf-8")
    declaration_source = DECLARATION_PATH.read_text(encoding="utf-8")
    telemetry_source = TELEMETRY_PATH.read_text(encoding="utf-8")
    capabilities_source = read_capability_source()

    assert "/advisory/policy-evaluations/{evaluation_id}/workflow" in routes_source
    assert "/advisory/policy-evaluations/{evaluation_id}/sign-off-decisions" in routes_source
    assert "rfc0025.policy-sign-off-workflow.v1" in supportability_source
    assert "POLICY_EVALUATION_SIGN_OFF_REQUIRES_MAKER_CHECKER" in workflow_source
    assert "CONFLICT_REVIEW_OUTCOME_REQUIRED" in workflow_source
    assert "PolicyEvaluationWorkflowResponse" in workflow_models_source
    assert "PolicyEvaluationSignOffDecisionRequest" in workflow_models_source
    assert "PolicyEvaluationWorkflowResponse" in compatibility_models_source
    assert "PolicyEvaluationSignOffDecisionRequest" in compatibility_models_source
    assert "/advisory/policy-evaluations/{evaluation_id}/workflow" in declaration_source
    assert "/advisory/policy-evaluations/{evaluation_id}/sign-off-decisions" in declaration_source
    assert "RFC-0025-slice-9-policy-approval-consent-signoff-workflow.md" in telemetry_source
    assert "Advise source workflow projection and sign-off decision recording" in supported_features
    assert (
        "Slice 12 is complete for Gateway and Workbench product realization" in supported_features
    )
    assert "policy report-package realization" in supported_features
    assert "active data-product promotion" in supported_features
    assert "client-ready publication" in supported_features
    assert "advisory.proposals.policy_evaluation" in capabilities_source
    assert "advisory_policy_evaluation" in capabilities_source
