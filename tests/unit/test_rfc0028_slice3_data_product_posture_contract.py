from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RFC28_PATH = REPO_ROOT / "docs" / "rfcs" / "RFC-0028-bank-demo-journey-and-client-ready-proof.md"
PRODUCT_DECLARATION_PATH = (
    REPO_ROOT / "contracts" / "domain-data-products" / "lotus-advise-products.v1.json"
)
TRUST_TELEMETRY_DIR = REPO_ROOT / "contracts" / "trust-telemetry"
CAPABILITY_MODULE_PATHS = (
    REPO_ROOT / "src" / "api" / "capabilities" / "service.py",
    REPO_ROOT / "src" / "api" / "capabilities" / "feature_catalog.py",
    REPO_ROOT / "src" / "api" / "capabilities" / "workflow_catalog.py",
)

RFC28_PROPOSED_RECORDS = {
    "AdvisoryBankDemoProofPack",
    "AdvisorySupportedClaimRegister",
    "AdvisoryDemoScenarioContract",
}

RFC28_COMPOSITION_PRODUCTS = {
    "ProposalNarrativeEvidence",
    "AdvisoryProposalMemoEvidencePack",
    "AdvisoryPolicyEvaluationRecord",
    "AdvisorCockpitOperatingSnapshot",
    "AdvisoryActionItemRegister",
    "AdvisoryCopilotInteractionRecord",
}


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _flat(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_rfc0028_keeps_proof_records_internal_but_promotes_capability_after_proof() -> None:
    declaration = _load_json(PRODUCT_DECLARATION_PATH)
    products = {product["product_name"]: product for product in declaration["products"]}
    telemetry_text = "\n".join(
        path.read_text(encoding="utf-8") for path in TRUST_TELEMETRY_DIR.glob("*.json")
    )
    capability_text = "\n".join(
        path.read_text(encoding="utf-8") for path in CAPABILITY_MODULE_PATHS
    )

    assert RFC28_PROPOSED_RECORDS.isdisjoint(products)
    for proposed_record in RFC28_PROPOSED_RECORDS:
        assert proposed_record not in telemetry_text

    assert "BANK_DEMO_PROOF_PACK_CREATED" not in capability_text
    assert "AdvisoryBankDemoProofPack" not in capability_text
    assert "AdvisorySupportedClaimRegister" not in capability_text
    assert "AdvisoryDemoScenarioContract" not in capability_text
    assert "advisory.bank_demo_proof" in capability_text
    assert "advisory_bank_demo_proof" in capability_text
    assert "supported-claim register" in capability_text


def test_rfc0028_composes_from_existing_active_advisory_evidence_products() -> None:
    declaration = _load_json(PRODUCT_DECLARATION_PATH)
    products = {product["product_name"]: product for product in declaration["products"]}

    assert RFC28_COMPOSITION_PRODUCTS.issubset(products)
    for product_name in RFC28_COMPOSITION_PRODUCTS:
        product = products[product_name]
        assert product["lifecycle_status"] == "active"
        assert product["owner_repository"] == "lotus-advise"
        assert product["authoritative_domain"] == "advisory_workflow"


def test_rfc0028_records_data_product_boundary_and_later_capability_promotion() -> None:
    flat = _flat(RFC28_PATH)

    markers = (
        "RFC-0028 proof-pack and supported-claim records remain internal/proposed",
        (
            "No `AdvisoryBankDemoProofPack`, `AdvisorySupportedClaimRegister`, or "
            "`AdvisoryDemoScenarioContract` active data product"
        ),
        (
            "Existing active Advise evidence products are the source products for the "
            "eventual RFC-0028 proof pack"
        ),
        (
            "`/platform/capabilities` must not advertise bank-demo proof or supported-claim "
            "support before the Advise proof API and the Gateway/Workbench proof slices "
            "promote the capability with evidence"
        ),
        (
            "Slice 17 promotes `/platform/capabilities` feature `advisory.bank_demo_proof` "
            "and workflow `advisory_bank_demo_proof`"
        ),
        (
            "`AdvisoryBankDemoProofPack`, `AdvisorySupportedClaimRegister`, and "
            "`AdvisoryDemoScenarioContract` remain internal proof records rather than active "
            "standalone data products"
        ),
    )
    for marker in markers:
        assert marker in flat
