from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PLATFORM_ROOT = REPO_ROOT.parent / "lotus-platform"
TELEMETRY_DIR = REPO_ROOT / "contracts" / "trust-telemetry"
SNAPSHOT_PATH = TELEMETRY_DIR / "advisory-proposal-lifecycle-record.telemetry.v1.json"
NARRATIVE_SNAPSHOT_PATH = TELEMETRY_DIR / "proposal-narrative-evidence.telemetry.v1.json"
MEMO_SNAPSHOT_PATH = TELEMETRY_DIR / "advisory-proposal-memo-evidence-pack.telemetry.v1.json"
POLICY_SNAPSHOT_PATH = TELEMETRY_DIR / "advisory-policy-evaluation-record.telemetry.v1.json"
COCKPIT_SNAPSHOT_PATH = TELEMETRY_DIR / "advisor-cockpit-operating-snapshot.telemetry.v1.json"
ACTION_REGISTER_SNAPSHOT_PATH = TELEMETRY_DIR / "advisory-action-item-register.telemetry.v1.json"
COPILOT_SNAPSHOT_PATH = TELEMETRY_DIR / "advisory-copilot-interaction-record.telemetry.v1.json"
DECLARATION_PATH = (
    REPO_ROOT / "contracts" / "domain-data-products" / "lotus-advise-products.v1.json"
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_platform_automation_module(module_name: str):
    module_path = PLATFORM_ROOT / "automation" / f"{module_name}.py"
    if not module_path.exists():
        pytest.skip(f"lotus-platform {module_name} automation is not available")
    automation_path = str(PLATFORM_ROOT / "automation")
    if automation_path not in sys.path:
        sys.path.insert(0, automation_path)
    return importlib.import_module(module_name)


def _load_platform_validator():
    return _load_platform_automation_module("validate_trust_telemetry")


def _write_current_domain_product_catalog(output_directory: Path) -> Path:
    discovery = _load_platform_automation_module("domain_product_discovery")
    discovery.write_discovery_artifacts(
        output_directory,
        discovery.DEFAULT_DECLARATION_DIRECTORY,
        generated_at_utc="2026-05-26T00:00:00Z",
        source_manifest_path=discovery.DEFAULT_SOURCE_MANIFEST_PATH,
    )
    return output_directory / "domain-product-catalog.json"


def test_advisory_proposal_lifecycle_trust_telemetry_validates_with_platform_contract(
    tmp_path: Path,
) -> None:
    validator = _load_platform_validator()
    catalog_path = _write_current_domain_product_catalog(tmp_path)

    issues = validator.validate_trust_telemetry_path(
        TELEMETRY_DIR,
        catalog_path=catalog_path,
    )

    assert issues == []


def test_advisory_proposal_lifecycle_trust_telemetry_is_tied_to_repo_declaration() -> None:
    snapshot = _load_json(SNAPSHOT_PATH)
    declaration = _load_json(DECLARATION_PATH)
    declared_product = next(
        product
        for product in declaration["products"]
        if product["product_name"] == "AdvisoryProposalLifecycleRecord"
    )

    assert snapshot["product_id"] == "lotus-advise:AdvisoryProposalLifecycleRecord:v1"
    assert snapshot["producer_repository"] == declaration["producer_repository"]
    assert snapshot["product_name"] == declared_product["product_name"]
    assert snapshot["product_version"] == declared_product["product_version"]
    assert (
        snapshot["freshness"]["freshness_class"]
        == (declared_product["freshness_policy"]["freshness_class"])
    )
    assert set(snapshot["observed_trust_metadata"]) == set(
        declared_product["required_trust_metadata"]
    )
    assert snapshot["lineage"]["lineage_materialized"] is True
    assert (
        snapshot["lineage"]["evidence_access_class"]
        == (declared_product["lineage_policy"]["evidence_access_class_ref"])
    )
    assert snapshot["blocking"]["blocked"] is False


def test_rfc0023_proposal_narrative_trust_telemetry_is_tied_to_repo_declaration() -> None:
    snapshot = _load_json(NARRATIVE_SNAPSHOT_PATH)
    declaration = _load_json(DECLARATION_PATH)
    declared_product = next(
        product
        for product in declaration["products"]
        if product["product_name"] == "ProposalNarrativeEvidence"
    )

    assert snapshot["product_id"] == "lotus-advise:ProposalNarrativeEvidence:v1"
    assert snapshot["producer_repository"] == declaration["producer_repository"]
    assert snapshot["product_name"] == declared_product["product_name"]
    assert snapshot["product_version"] == declared_product["product_version"]
    assert (
        snapshot["freshness"]["freshness_class"]
        == (declared_product["freshness_policy"]["freshness_class"])
    )
    assert set(snapshot["observed_trust_metadata"]) == set(
        declared_product["required_trust_metadata"]
    )
    assert snapshot["lineage"]["lineage_materialized"] is True
    assert (
        snapshot["lineage"]["evidence_access_class"]
        == (declared_product["lineage_policy"]["evidence_access_class_ref"])
    )
    assert snapshot["blocking"]["blocked"] is False


def test_rfc0023_proposal_narrative_trust_telemetry_does_not_promote_client_ready() -> None:
    telemetry_files = {path.name for path in TELEMETRY_DIR.glob("*.json")}
    snapshot = _load_json(NARRATIVE_SNAPSHOT_PATH)
    snapshot_text = json.dumps(snapshot, sort_keys=True).lower()

    assert "proposal-narrative-evidence.telemetry.v1.json" in telemetry_files
    assert snapshot["product_name"] == "ProposalNarrativeEvidence"
    assert "client-ready publication" not in snapshot_text
    assert "client_ready" not in snapshot_text
    assert "compliance-review" not in snapshot_text


def test_rfc0024_memo_trust_telemetry_is_tied_to_active_declaration() -> None:
    snapshot = _load_json(MEMO_SNAPSHOT_PATH)
    declaration = _load_json(DECLARATION_PATH)
    declared_product = next(
        product
        for product in declaration["products"]
        if product["product_name"] == "AdvisoryProposalMemoEvidencePack"
    )

    assert snapshot["product_id"] == "lotus-advise:AdvisoryProposalMemoEvidencePack:v1"
    assert snapshot["producer_repository"] == declaration["producer_repository"]
    assert snapshot["product_name"] == declared_product["product_name"]
    assert snapshot["product_version"] == declared_product["product_version"]
    assert declared_product["lifecycle_status"] == "active"
    assert (
        "/advisory/proposals/{proposal_id}/versions/{version_no}/memos"
        in (declared_product["current_routes"])
    )
    assert (
        snapshot["freshness"]["freshness_class"]
        == declared_product["freshness_policy"]["freshness_class"]
    )
    assert set(snapshot["observed_trust_metadata"]) == set(
        declared_product["required_trust_metadata"]
    )
    assert snapshot["lineage"]["lineage_materialized"] is True
    assert (
        snapshot["lineage"]["evidence_access_class"]
        == declared_product["lineage_policy"]["evidence_access_class_ref"]
    )
    assert snapshot["blocking"]["blocked"] is False


def test_rfc0024_memo_trust_telemetry_promotes_only_advisor_use_memo() -> None:
    telemetry_files = {path.name for path in TELEMETRY_DIR.glob("*.json")}
    snapshot = _load_json(MEMO_SNAPSHOT_PATH)
    declaration = _load_json(DECLARATION_PATH)
    supported_text = (REPO_ROOT / "wiki" / "Supported-Features.md").read_text(encoding="utf-8")
    capability_text = (REPO_ROOT / "src" / "api" / "capabilities" / "service.py").read_text(
        encoding="utf-8"
    )

    assert "advisory-proposal-memo-evidence-pack.telemetry.v1.json" in telemetry_files
    assert snapshot["product_name"] == "AdvisoryProposalMemoEvidencePack"
    assert snapshot["completeness_status"] == "complete"
    assert "Slice 7 is complete for canonical `lotus-advise` memo" in supported_text
    assert "AdvisoryProposalMemoEvidencePack:v1` is active" in supported_text
    assert "Gateway, Workbench, report/render/archive realization" in supported_text
    assert "client-ready memo claims remain planned" in supported_text
    assert "full bank-demo/RFP claims" in supported_text
    assert "AdvisoryProposalMemoEvidencePack:v1 | Supported" in supported_text
    assert "advisory.proposals.memo_evidence_pack" in capability_text

    declared_product = next(
        product
        for product in declaration["products"]
        if product["product_name"] == "AdvisoryProposalMemoEvidencePack"
    )
    declaration_text = json.dumps(declared_product, sort_keys=True).lower()
    assert "client-ready memo publication" in declaration_text
    assert "external client communication remain blocked" in declaration_text


def test_rfc0025_policy_evaluation_trust_telemetry_is_active_and_tied_to_declaration() -> None:
    snapshot = _load_json(POLICY_SNAPSHOT_PATH)
    declaration = _load_json(DECLARATION_PATH)
    declared_product = next(
        product
        for product in declaration["products"]
        if product["product_name"] == "AdvisoryPolicyEvaluationRecord"
    )

    assert snapshot["product_id"] == "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
    assert snapshot["producer_repository"] == declaration["producer_repository"]
    assert snapshot["product_name"] == declared_product["product_name"]
    assert snapshot["product_version"] == declared_product["product_version"]
    assert declared_product["lifecycle_status"] == "active"
    assert declared_product["current_routes"] == [
        "/advisory/proposals/{proposal_id}/versions/{proposal_version_id}/policy-evaluations",
        "/advisory/policy-evaluations/review-queue",
        "/advisory/policy-evaluations/{evaluation_id}",
        "/advisory/policy-evaluations/{evaluation_id}/replay",
        "/advisory/policy-evaluations/{evaluation_id}/events",
        "/advisory/policy-evaluations/{evaluation_id}/lineage",
        "/advisory/policy-evaluations/{evaluation_id}/sign-off-package",
        "/advisory/policy-evaluations/{evaluation_id}/workflow",
        "/advisory/policy-evaluations/{evaluation_id}/sign-off-decisions",
        "/advisory/policy-evaluations/{evaluation_id}/report-packages",
        "/advisory/policy-evaluations/{evaluation_id}/ai-evidence",
    ]
    assert (
        snapshot["freshness"]["freshness_class"]
        == declared_product["freshness_policy"]["freshness_class"]
    )
    assert snapshot["freshness"]["freshness_state"] == "current"
    assert snapshot["completeness_status"] == "complete"
    assert snapshot["data_quality_status"] == "quality_passed"
    assert set(snapshot["observed_trust_metadata"]) == set(
        declared_product["required_trust_metadata"]
    )
    assert snapshot["lineage"]["lineage_materialized"] is True
    assert (
        "lotus-advise://docs/rfcs/RFC-0025-slice-7-policy-evaluation-persistence-replay-audit.md"
        in snapshot["lineage"]["evidence_uris"]
    )
    assert (
        "lotus-advise://docs/rfcs/RFC-0025-slice-8-certified-apis-and-openapi.md"
        in snapshot["lineage"]["evidence_uris"]
    )
    assert (
        "lotus-advise://docs/rfcs/RFC-0025-slice-9-policy-approval-consent-signoff-workflow.md"
        in snapshot["lineage"]["evidence_uris"]
    )
    assert (
        "lotus-advise://docs/rfcs/RFC-0025-slice-10-report-render-archive-realization.md"
        in snapshot["lineage"]["evidence_uris"]
    )
    assert (
        "lotus-advise://docs/rfcs/RFC-0025-slice-11-ai-policy-evidence-boundary.md"
        in snapshot["lineage"]["evidence_uris"]
    )
    assert (
        "lotus-advise://docs/rfcs/RFC-0025-slice-12-gateway-workbench-product-realization.md"
        in snapshot["lineage"]["evidence_uris"]
    )
    assert (
        "lotus-advise://docs/rfcs/RFC-0025-slice-13-commercial-demo-rfp-support.md"
        in snapshot["lineage"]["evidence_uris"]
    )
    assert (
        "lotus-advise://docs/rfcs/RFC-0025-slice-14-implementation-proof.md"
        in snapshot["lineage"]["evidence_uris"]
    )
    assert (
        "lotus-advise://docs/rfcs/RFC-0025-slice-15-final-hardening-and-review.md"
        in snapshot["lineage"]["evidence_uris"]
    )
    assert (
        "lotus-advise://docs/rfcs/RFC-0025-slice-16-final-closure.md"
        in snapshot["lineage"]["evidence_uris"]
    )
    assert (
        "lotus-advise://src/core/policy_packs/workflow.py" in snapshot["lineage"]["evidence_uris"]
    )
    assert (
        "lotus-advise://src/core/policy_packs/reporting.py" in snapshot["lineage"]["evidence_uris"]
    )
    assert "lotus-advise://src/core/policy_packs/ai.py" in snapshot["lineage"]["evidence_uris"]
    assert (
        "lotus-advise://src/integrations/lotus_ai/policy_evidence.py"
        in snapshot["lineage"]["evidence_uris"]
    )
    assert (
        snapshot["lineage"]["evidence_access_class"]
        == declared_product["lineage_policy"]["evidence_access_class_ref"]
    )
    assert snapshot["blocking"] == {"blocked": False}
    assert (
        "active advisor/compliance policy evidence data product"
        in (snapshot["evidence"]["claim_boundary"])
    )
    assert "canonical live proof" not in snapshot["evidence"]["claim_boundary"]
    assert "approval/waiver authority" in snapshot["evidence"]["claim_boundary"]


def test_rfc0025_policy_evaluation_catalog_generation_promotes_active_support(
    tmp_path: Path,
) -> None:
    catalog_path = _write_current_domain_product_catalog(tmp_path)
    catalog = _load_json(catalog_path)
    policy_product = next(
        product
        for product in catalog["products"]
        if product["product_id"] == "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
    )
    capability_text = (REPO_ROOT / "src" / "api" / "capabilities" / "service.py").read_text(
        encoding="utf-8"
    )

    assert policy_product["lifecycle_status"] == "active"
    assert policy_product["current_routes"] == [
        "/advisory/proposals/{proposal_id}/versions/{proposal_version_id}/policy-evaluations",
        "/advisory/policy-evaluations/review-queue",
        "/advisory/policy-evaluations/{evaluation_id}",
        "/advisory/policy-evaluations/{evaluation_id}/replay",
        "/advisory/policy-evaluations/{evaluation_id}/events",
        "/advisory/policy-evaluations/{evaluation_id}/lineage",
        "/advisory/policy-evaluations/{evaluation_id}/sign-off-package",
        "/advisory/policy-evaluations/{evaluation_id}/workflow",
        "/advisory/policy-evaluations/{evaluation_id}/sign-off-decisions",
        "/advisory/policy-evaluations/{evaluation_id}/report-packages",
        "/advisory/policy-evaluations/{evaluation_id}/ai-evidence",
    ]
    assert policy_product["completeness_policy"]["default_status"] == "complete"
    assert (
        "Gateway/Workbench visibility"
        in policy_product["freshness_policy"]["max_allowed_age_description"]
    )
    assert (
        "final closure evidence"
        in policy_product["freshness_policy"]["max_allowed_age_description"]
    )
    assert (
        "live-suite implementation proof"
        in policy_product["freshness_policy"]["max_allowed_age_description"]
    )
    assert (
        "canonical live proof"
        not in policy_product["freshness_policy"]["max_allowed_age_description"]
    )
    assert (
        "approval/waiver authority"
        in policy_product["freshness_policy"]["max_allowed_age_description"]
    )
    assert "advisory.proposals.policy_evaluation" in capability_text
    assert "advisory_policy_evaluation" in capability_text


def test_rfc0026_cockpit_trust_telemetry_is_active_and_tied_to_declaration() -> None:
    declaration = _load_json(DECLARATION_PATH)
    declared_products = {product["product_name"]: product for product in declaration["products"]}

    for snapshot_path, product_name in (
        (COCKPIT_SNAPSHOT_PATH, "AdvisorCockpitOperatingSnapshot"),
        (ACTION_REGISTER_SNAPSHOT_PATH, "AdvisoryActionItemRegister"),
    ):
        snapshot = _load_json(snapshot_path)
        declared_product = declared_products[product_name]

        assert snapshot["product_id"] == f"lotus-advise:{product_name}:v1"
        assert snapshot["producer_repository"] == declaration["producer_repository"]
        assert snapshot["product_name"] == declared_product["product_name"]
        assert snapshot["product_version"] == declared_product["product_version"]
        assert declared_product["lifecycle_status"] == "active"
        assert (
            snapshot["freshness"]["freshness_class"]
            == declared_product["freshness_policy"]["freshness_class"]
        )
        assert snapshot["freshness"]["freshness_state"] == "current"
        assert snapshot["completeness_status"] == "complete"
        assert snapshot["data_quality_status"] == "quality_passed"
        assert set(snapshot["observed_trust_metadata"]) == set(
            declared_product["required_trust_metadata"]
        )
        assert snapshot["lineage"]["lineage_materialized"] is True
        assert (
            snapshot["lineage"]["evidence_access_class"]
            == declared_product["lineage_policy"]["evidence_access_class_ref"]
        )
        assert snapshot["blocking"] == {"blocked": False}
        assert "canonical PB_SG_GLOBAL_BAL_001 live proof" in snapshot["evidence"]["claim_boundary"]
        assert "client-ready publication" in snapshot["evidence"]["claim_boundary"]
        assert "OMS order lifecycle" in snapshot["evidence"]["claim_boundary"]


def test_rfc0027_copilot_trust_telemetry_is_active_and_tied_to_declaration() -> None:
    snapshot = _load_json(COPILOT_SNAPSHOT_PATH)
    declaration = _load_json(DECLARATION_PATH)
    declared_product = next(
        product
        for product in declaration["products"]
        if product["product_name"] == "AdvisoryCopilotInteractionRecord"
    )

    assert snapshot["product_id"] == "lotus-advise:AdvisoryCopilotInteractionRecord:v1"
    assert snapshot["producer_repository"] == declaration["producer_repository"]
    assert snapshot["product_name"] == declared_product["product_name"]
    assert snapshot["product_version"] == declared_product["product_version"]
    assert declared_product["lifecycle_status"] == "active"
    assert "AdvisoryCopilotEvidencePacket" not in {
        product["product_name"] for product in declaration["products"]
    }
    assert "AdvisoryCopilotReviewRecord" not in {
        product["product_name"] for product in declaration["products"]
    }
    assert "/advisory/copilot/actions" in declared_product["current_routes"]
    assert (
        "/advisory/proposals/{proposal_id}/versions/{version_id}/copilot-runs"
        in declared_product["current_routes"]
    )
    assert (
        snapshot["freshness"]["freshness_class"]
        == declared_product["freshness_policy"]["freshness_class"]
    )
    assert snapshot["freshness"]["freshness_state"] == "current"
    assert snapshot["completeness_status"] == "complete"
    assert snapshot["data_quality_status"] == "quality_passed"
    assert set(snapshot["observed_trust_metadata"]) == set(
        declared_product["required_trust_metadata"]
    )
    assert snapshot["lineage"]["lineage_materialized"] is True
    assert (
        snapshot["lineage"]["evidence_access_class"]
        == declared_product["lineage_policy"]["evidence_access_class_ref"]
    )
    assert (
        "lotus-workbench://output/playwright/live-canonical/live-validation-summary.json#ADVISORY_COPILOT_CANONICAL_PROOF_CREATED"
        in snapshot["lineage"]["evidence_uris"]
    )
    assert snapshot["blocking"] == {"blocked": False}
    assert "reviewed internal advisor/reviewer copilot interaction product" in (
        snapshot["evidence"]["claim_boundary"]
    )
    assert "Evidence packets and review events remain audit records" in (
        snapshot["evidence"]["claim_boundary"]
    )
    claim_boundary = snapshot["evidence"]["claim_boundary"].lower()
    assert "client-ready publication" in claim_boundary
    assert "policy approval/sign-off authority" in claim_boundary
    assert "oms order lifecycle" in claim_boundary
