from pathlib import Path

SLICE15_PATH = Path("docs/rfcs/RFC-0025-slice-15-final-hardening-and-review.md")
SUPPORTABILITY_PATH = Path("src/core/policy_packs/supportability.py")


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_rfc0025_slice15_hardening_is_indexed() -> None:
    slice15_text = _read(SLICE15_PATH)
    rfc_text = _read("docs/rfcs/RFC-0025-enterprise-suitability-and-best-interest-policy-packs.md")
    rfc_index = _read("docs/rfcs/README.md")
    wiki_index = _read("wiki/RFC-Index.md")
    supported_features = _read("wiki/Supported-Features.md")
    repo_context = _read("REPOSITORY-ENGINEERING-CONTEXT.md")

    source_ref = "docs/rfcs/RFC-0025-slice-15-final-hardening-and-review.md"
    assert source_ref in rfc_text
    assert source_ref in rfc_index
    assert source_ref in wiki_index

    assert "supportability vocabulary" in slice15_text
    assert "Gateway and Workbench product support" in slice15_text
    assert "signed-off report-package handoff support" in slice15_text
    assert "active data-product promotion blocked until final closure" in slice15_text
    assert "RFC-0025 is implemented for advisor/compliance policy evidence through Slice 17" in (
        supported_features
    )
    assert "centralizing policy-pack supportability" in repo_context


def test_rfc0025_slice15_supportability_truth_is_centralized_and_current() -> None:
    supportability = _read(SUPPORTABILITY_PATH)
    catalog = _read("src/core/policy_packs/catalog.py")
    catalog_definitions = _read("src/core/policy_packs/catalog_definitions.py")
    evaluation = _read("src/core/policy_packs/evaluation.py")
    persistence = _read("src/core/policy_packs/persistence.py")
    persistence_projection = _read("src/core/policy_packs/persistence_projection.py")
    workflow = _read("src/core/policy_packs/workflow.py")
    policy_api_routes = _read("src/api/proposals/routes_policy_evaluations.py")

    assert "def policy_runtime_supportability" in supportability
    assert '"gateway_supported": True' in supportability
    assert '"gateway_support": "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_BFF"' in supportability
    assert '"workbench_supported": True' in supportability
    assert '"workbench_support": "SUPPORTED_BY_RFC0025_SLICE12_GATEWAY_ONLY_UI"' in supportability
    assert (
        '"report_package_realization": "SUPPORTED_BY_RFC0025_SLICE10_SIGNED_OFF_PACKAGE"'
        in supportability
    )
    assert (
        '"active_data_product_promotion": "SUPPORTED_BY_RFC0025_SLICE16_FINAL_CLOSURE"'
        in supportability
    )
    assert '"mesh_certification": "SUPPORTED_BY_RFC0025_SLICE16_FINAL_CLOSURE"' in supportability
    assert '"client_ready_publication": CLIENT_READY_PUBLICATION_POSTURE' in supportability

    assert "catalog_posture()" in catalog
    assert "policy_runtime_supportability()" in catalog_definitions
    assert "policy_runtime_supportability()" in evaluation
    assert "policy_evaluation_api_posture()" in persistence
    assert "policy_runtime_supportability()" in persistence_projection
    assert "policy_sign_off_package_posture()" in workflow

    combined = "\n".join([catalog, evaluation, persistence, workflow, policy_api_routes])
    assert '"gateway_supported": False' not in combined
    assert '"workbench_supported": False' not in combined
    assert "report realization, and client-ready publication remain gated" not in combined
    assert "Gateway/Workbench consumption and signed-off report-package handoff are supported" in (
        policy_api_routes
    )
