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
DECLARATION_PATH = (
    REPO_ROOT / "contracts" / "domain-data-products" / "lotus-advise-products.v1.json"
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_platform_validator():
    validator_path = PLATFORM_ROOT / "automation" / "validate_trust_telemetry.py"
    if not validator_path.exists():
        pytest.skip("lotus-platform trust telemetry validator is not available")
    automation_path = str(PLATFORM_ROOT / "automation")
    if automation_path not in sys.path:
        sys.path.insert(0, automation_path)
    return importlib.import_module("validate_trust_telemetry")


def test_advisory_proposal_lifecycle_trust_telemetry_validates_with_platform_contract() -> None:
    validator = _load_platform_validator()

    issues = validator.validate_trust_telemetry_path(
        TELEMETRY_DIR,
        catalog_path=PLATFORM_ROOT / "generated" / "domain-product-catalog.json",
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


def test_rfc0024_memo_trust_telemetry_is_tied_to_proposed_declaration() -> None:
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
    assert declared_product["lifecycle_status"] == "proposed"
    assert "current_routes" not in declared_product
    assert (
        snapshot["freshness"]["freshness_class"]
        == declared_product["freshness_policy"]["freshness_class"]
    )
    assert set(snapshot["observed_trust_metadata"]) == set(
        declared_product["required_trust_metadata"]
    )
    assert snapshot["lineage"]["lineage_materialized"] is False
    assert (
        snapshot["lineage"]["evidence_access_class"]
        == declared_product["lineage_policy"]["evidence_access_class_ref"]
    )
    assert snapshot["blocking"]["blocked"] is True


def test_rfc0024_memo_trust_telemetry_does_not_promote_supported_memo() -> None:
    telemetry_files = {path.name for path in TELEMETRY_DIR.glob("*.json")}
    snapshot = _load_json(MEMO_SNAPSHOT_PATH)
    declaration = _load_json(DECLARATION_PATH)
    supported_text = (REPO_ROOT / "wiki" / "Supported-Features.md").read_text(encoding="utf-8")
    capability_text = (REPO_ROOT / "src" / "api" / "capabilities" / "service.py").read_text(
        encoding="utf-8"
    )

    assert "advisory-proposal-memo-evidence-pack.telemetry.v1.json" in telemetry_files
    assert snapshot["product_name"] == "AdvisoryProposalMemoEvidencePack"
    assert snapshot["completeness_status"] == "blocked"
    assert "Memo generation, memo APIs, memo persistence" in supported_text
    assert "client-ready memo claims remain planned" in supported_text
    assert "AdvisoryProposalMemoEvidencePack:v1 | Supported" not in supported_text
    assert "advisory.proposals.memo_evidence_pack" not in capability_text

    declared_product = next(
        product
        for product in declaration["products"]
        if product["product_name"] == "AdvisoryProposalMemoEvidencePack"
    )
    declaration_text = json.dumps(declared_product, sort_keys=True).lower()
    assert "client-ready memo publication" not in declaration_text
    assert "memo support" not in declaration_text
