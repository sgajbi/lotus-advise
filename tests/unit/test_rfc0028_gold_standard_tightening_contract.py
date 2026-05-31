from __future__ import annotations

from pathlib import Path

RFC28_PATH = Path("docs/rfcs/RFC-0028-bank-demo-journey-and-client-ready-proof.md")
RFC_INDEX_PATH = Path("docs/rfcs/README.md")
WIKI_RFC_INDEX_PATH = Path("wiki/RFC-Index.md")
WIKI_SUPPORTED_FEATURES_PATH = Path("wiki/Supported-Features.md")
COMMERCIAL_GUIDE_PATH = Path("docs/commercial/RFC-0028-bank-demo-client-proof-materials.md")
DEMO_README_PATH = Path("docs/demo/README.md")
REPO_CONTEXT_PATH = Path("REPOSITORY-ENGINEERING-CONTEXT.md")
README_PATH = Path("README.md")
WIKI_API_SURFACE_PATH = Path("wiki/API-Surface.md")
WIKI_SECURITY_PATH = Path("wiki/Security-and-Governance.md")
WIKI_OPERATIONS_PATH = Path("wiki/Operations-Runbook.md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_rfc0028_locks_slice_zero_decisions_before_implementation() -> None:
    rfc = _read(RFC28_PATH)
    flat = _flat(RFC28_PATH)

    assert "Last Tightened** | 2026-05-31" in rfc
    assert "rfc0028-gold-standard-implementation" in rfc
    assert "## 22. Slice 0 Pre-Implementation Decisions" in rfc
    assert "## 22. Open Questions" not in rfc
    assert "No open implementation question remains for RFC-0028 Slice 1" in rfc

    required_decisions = (
        "Hybrid. `lotus-advise` must implement an Advise-owned proof-pack and supported-claim API",
        "Script-only proof is insufficient for RFC-0028",
        "Primary dataset is `PB_SG_GLOBAL_BAL_001`",
        "RFC28_BANK_DEMO_CLIENT_READY_PROOF_CANONICAL",
        "First supported journey is the combined private-banking advisory scenario",
        "No Workbench component may reconstruct advisory suitability, memo, narrative, policy",
        "CLIENT_READY_REVIEW_REQUIRED",
        "CLIENT_READY_PUBLICATION_BLOCKED",
        "External certifications, bank-specific control attestations, SOC/ISO status",
        "Load, latency, SLO, DR/RTO/RPO, tenant, and legal-entity claims block closure only",
        (
            "Produce markdown source now for demo script, proof interpretation guide, "
            "RFP/security pack"
        ),
    )
    for decision in required_decisions:
        assert decision in flat


def test_rfc0028_requires_canonical_front_office_automation_and_lowest_layer_tests() -> None:
    flat = _flat(RFC28_PATH)

    automation_markers = (
        "RFC-0028 must expand canonical front-office automation",
        "BANK_DEMO_PROOF_PACK_CREATED",
        "PB_SG_GLOBAL_BAL_001",
        "WorkBench evidence is not demo-ready",
    )
    for marker in automation_markers:
        assert marker.lower() in flat.lower()

    test_markers = (
        "Any live validation defect discovered during RFC-0028 must be covered",
        "unit for pure domain rules",
        "contract/API test for schema and route behavior",
        "integration test for cross-service contracts",
        "front-office/live validation for product-surface regressions",
    )
    for marker in test_markers:
        assert marker in flat


def test_rfc0028_records_platform_slice_one_supported_claim_scaffolding() -> None:
    flat = _flat(RFC28_PATH)

    markers = (
        "A reusable platform gap exists",
        "1f46cd764b1e8437091c6d5e567403053b899313",
        "ea6e8151d253f5d738dfb5902d8193238b946bba",
        "PR #366",
        "26554797152",
        "supported-claim-register.schema.json",
        "validate_supported_claim_register.py",
        "test_supported_claim_register_contract.py",
        "No Advise-local claim taxonomy may diverge from the platform validator",
    )
    for marker in markers:
        assert marker in flat


def test_rfc0028_indexes_record_platform_slice_one_without_promotion() -> None:
    rfc_index = _flat(RFC_INDEX_PATH)
    wiki_index = _flat(WIKI_RFC_INDEX_PATH)
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    index_markers = (
        "RFC28_BANK_DEMO_CLIENT_READY_PROOF_CANONICAL",
        "BANK_DEMO_PROOF_PACK_CREATED",
        "PB_SG_GLOBAL_BAL_001",
        "PR #366",
        "26554797152",
        "AdvisoryJourneyIntegrationProofSummary:v1",
        "journey-integration-proof-summary.json",
        "RFC0028_JOURNEY_INTEGRATION_PROOF_CREATED",
        "ai_policy_cockpit_proof_integrated",
        "commercial-material-pack.json",
        "RFC0028_COMMERCIAL_MATERIAL_PACK_CREATED",
        "commercial_rfp_security_material_available",
    )
    for marker in index_markers:
        assert marker in rfc_index
        assert marker in wiki_index or marker in supported_features

    assert "advisory.bank_demo_proof" in supported_features
    assert "advisory-bank-demo-proof-live.png" in wiki_index
    assert "RFP response" in supported_features
    assert "client-ready publication" in supported_features
    assert "DRAFT - SLICE 0 DECISIONS LOCKED" not in rfc_index
    assert "DRAFT - SLICE 0 DECISIONS LOCKED" not in wiki_index
    assert "Draft with Slice 0 decisions locked" not in supported_features
    assert (
        "IMPLEMENTED - bank-demo proof and claim-controlled commercial material complete"
        in rfc_index
    )
    assert "RFC-0028 is implemented for repeatable bank-demo proof" in wiki_index
    assert "Implemented for source scenario contracts" in supported_features
    assert "DRAFT - SLICES 0-12 DOCUMENTATION PRODUCT TRUTH COMPLETE" not in rfc_index
    assert "DRAFT - SLICES 0-12 DOCUMENTATION PRODUCT TRUTH COMPLETE" not in wiki_index
    assert "DRAFT - SLICES 0-12 DOCUMENTATION PRODUCT TRUTH COMPLETE" not in supported_features
    assert "DRAFT - SLICES 0-12 DOCUMENTATION PRODUCT TRUTH COMPLETE" not in _flat(RFC28_PATH)


def test_rfc0028_records_slice_two_cleanup_scope_and_wiki_gate() -> None:
    flat = _flat(RFC28_PATH)

    markers = (
        "The first cleanup gap was durable documentation drift after Slice 1",
        "docs/rfcs/README.md",
        "wiki/RFC-Index.md",
        "wiki/Supported-Features.md",
        (
            "No Advise runtime code, controller, infrastructure module, "
            "or commercial asset was created"
        ),
        "Wiki source changed because supported-feature and RFC-index truth changed",
        "publication must happen after merge to `main`",
    )
    for marker in markers:
        assert marker in flat


def test_rfc0028_records_slice_four_proof_model_implementation() -> None:
    flat = _flat(RFC28_PATH)

    markers = (
        "src/core/bank_demo_proof/",
        "AdvisoryDemoScenarioContract:v1",
        "AdvisorySupportedClaimRegister:v1",
        "AdvisoryBankDemoProofPack:v1",
        "No controller, API route, persistence table, data-product declaration",
        "IMPLEMENTATION_BACKED` claims require evidence refs and proof requirements",
        "local-only or secret runtime assets cannot be commit-allowed",
        "commit-allowed proof assets must use commit-safe or customer-consumable access classes",
        "`COMMIT_SOURCE` retention, and a canonical content hash",
        "CLIENT_READY_APPROVED` is not part of the current proof-pack API contract",
        "tests/unit/advisory/engine/test_engine_bank_demo_proof_models.py",
    )
    for marker in markers:
        assert marker in flat
    assert "REMOVED_OR_SUPERSEDED" not in flat


def test_rfc0028_records_slice_five_backend_proof_capture() -> None:
    flat = _flat(RFC28_PATH)

    markers = (
        "src/core/bank_demo_proof/capture.py",
        "scripts/capture_rfc0028_backend_proof.py",
        "output/rfc0028/backend-proof",
        "metadata.json",
        "scenario-contract.json",
        "supported-claim-register.json",
        "proof-pack.json",
        "runtime-posture.json",
        "sanitized-runtime-summary.json",
        "material-field-review.json",
        "BANK_DEMO_PROOF_PACK_CREATED",
        "RFC0028_BACKEND_MATERIAL_FIELD_REVIEW_PASSED",
        "RFC0028_RUNTIME_POSTURE_CAPTURED",
        "CLIENT_READY_PUBLICATION_BLOCKED",
        "BACKEND_BACKED_UI_PENDING",
        "tests/unit/advisory/engine/test_engine_bank_demo_proof_capture.py",
        "tests/unit/scripts/test_capture_rfc0028_backend_proof.py",
    )
    for marker in markers:
        assert marker in flat


def test_rfc0028_records_slice_six_document_proof_capture() -> None:
    flat = _flat(RFC28_PATH)
    rfc_index = _flat(RFC_INDEX_PATH)
    wiki_index = _flat(WIKI_RFC_INDEX_PATH)
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    markers = (
        "AdvisoryDocumentProofSummary:v1",
        "src/core/bank_demo_proof/document_proof.py",
        "document-proof-summary.json",
        "RFC0028_DOCUMENT_PROOF_SUMMARY_CREATED",
        "advisor_use_document_proof_available",
        "BACKEND_BACKED_UI_PENDING",
        "OWNED_BY_LOTUS_ARCHIVE",
        "MEMO_CLIENT_READY_DOCUMENT_NOT_SUPPORTED",
        "POLICY_CLIENT_READY_DOCUMENT_NOT_SUPPORTED",
        "tests/unit/advisory/engine/test_engine_bank_demo_document_proof.py",
    )
    for marker in markers:
        assert marker in flat

    for source in (rfc_index, wiki_index, supported_features):
        assert (
            "DRAFT - SLICES 0-10 COMMERCIAL PROOF MATERIAL COMPLETE" in source
            or "Slices 0-10 are implementation-backed" in source
            or "Slice 8 closes Workbench proof" in source
        )
        assert "document-proof-summary.json" in source
        assert "client-ready document publication remains blocked" in source


def test_rfc0028_records_slice_seven_gateway_publication_without_product_overclaim() -> None:
    flat = _flat(RFC28_PATH)
    rfc_index = _flat(RFC_INDEX_PATH)
    wiki_index = _flat(WIKI_RFC_INDEX_PATH)
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    markers = (
        "Slice 7A Advise source API implementation decision and evidence",
        "GET /advisory/bank-demo-proof/scenario-contract",
        "GET /advisory/bank-demo-proof/supported-claim-register",
        "POST /advisory/bank-demo-proof/proof-packs",
        "src/api/routers/bank_demo_proof.py",
        "BackendProofCaptureBundle",
        "RFC0028_BACKEND_PROOF_MATERIAL_REVIEW_BLOCKED",
        "HTTP 409",
        "tests/unit/advisory/api/test_api_bank_demo_proof.py",
        "Slice 7B Gateway publication implementation decision and evidence",
        "lotus-gateway` PR #252",
        "f99ca1dfe074b57c99793ab1ca86542869d579a4",
        "GET /api/v1/advisory/bank-demo-proof/scenario-contract",
        "GET /api/v1/advisory/bank-demo-proof/supported-claim-register",
        "POST /api/v1/advisory/bank-demo-proof/proof-packs",
        "tests/unit/test_bank_demo_proof_service.py",
        "tests/integration/test_bank_demo_proof_router.py",
        "tests/contract/test_advise_gateway_route_coverage.py",
        "tests/unit/test_rfc0028_bank_demo_proof_documentation.py",
        "26559811341",
        "a73cd24",
    )
    for marker in markers:
        assert marker in flat

    for source in (rfc_index, wiki_index, supported_features):
        assert (
            "SLICES 0-10 COMMERCIAL PROOF MATERIAL COMPLETE" in source
            or "Slices 0-10 are implementation-backed" in source
            or "Slice 8 closes Workbench proof" in source
        )
        assert "Gateway consumption remains the next Slice 7 owner-repository step" not in source
        assert "screenshot" in source
        assert "RFP" in source
        assert "client-ready publication" in source
        assert "unpromoted" in source or "blocked" in source


def test_rfc0028_records_slice_nine_integration_proof_without_client_ready_overclaim() -> None:
    flat = _flat(RFC28_PATH)
    rfc_index = _flat(RFC_INDEX_PATH)
    wiki_index = _flat(WIKI_RFC_INDEX_PATH)
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH)

    markers = (
        "AdvisoryJourneyIntegrationProofSummary:v1",
        "src/core/bank_demo_proof/integration_proof.py",
        "journey-integration-proof-summary.json",
        "RFC0028_JOURNEY_INTEGRATION_PROOF_CREATED",
        "GOVERNANCE_INTEGRATION_SUMMARY",
        "ai_policy_cockpit_proof_integrated",
        "parity.proposal_policy.ai_raw_source_evidence_included",
        "advisory.advisor_cockpit",
        "advisory.suitability_review",
        "proposal.memo_evidence_pack",
        "advisory.bank_demo_proof",
        "tests/unit/advisory/api/test_api_bank_demo_proof.py",
    )
    for marker in markers:
        assert marker in flat

    for source in (rfc_index, wiki_index, supported_features):
        assert "Slice 9 adds" in source
        assert "AdvisoryJourneyIntegrationProofSummary:v1" in source
        assert "journey-integration-proof-summary.json" in source
        assert "RFC0028_JOURNEY_INTEGRATION_PROOF_CREATED" in source
        assert "ai_policy_cockpit_proof_integrated" in source
        assert "client-ready publication" in source
        assert "RFP" in source
        assert "OMS/order/fill/settlement" in source


def test_rfc0028_records_slice_ten_commercial_material_without_unsupported_claims() -> None:
    flat = _flat(RFC28_PATH)
    rfc_index = _flat(RFC_INDEX_PATH)
    wiki_index = _flat(WIKI_RFC_INDEX_PATH)
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH)
    commercial = _flat(COMMERCIAL_GUIDE_PATH)
    demo_readme = _read(DEMO_README_PATH)

    markers = (
        "AdvisoryCommercialMaterialPack:v1",
        "src/core/bank_demo_proof/commercial_materials.py",
        "commercial-material-pack.json",
        "RFC0028_COMMERCIAL_MATERIAL_PACK_CREATED",
        "COMMERCIAL_DOCUMENT",
        "commercial_rfp_security_material_available",
        "docs/commercial/RFC-0028-bank-demo-client-proof-materials.md",
        "tests/unit/scripts/test_capture_rfc0028_backend_proof.py",
    )
    for marker in markers:
        assert marker in flat

    for heading in (
        "## Implementation-Backed Product One-Pager",
        "## Supported-Claim Mapping",
        "## RFP Response Pack",
        "## Security Posture Pack",
        "## Deck-Ready Architecture Outline",
        "## Demo Script And Talk Track",
        "## Proof-Pack Interpretation Guide",
        "## ROI Story",
        "## Supported Versus Blocked Feature Matrix",
        "## Client-Demo Boundaries",
        "## Operator And Demo-Lead Checklist",
    ):
        assert heading in commercial

    for source in (rfc_index, wiki_index, supported_features, demo_readme):
        assert "commercial-material-pack.json" in source or "bank-demo-client-proof-materials" in (
            source
        )
        assert "commercial_rfp_security_material_available" in source or (
            "claim-controlled commercial support guide" in source
        )
        assert "client-ready publication" in source
        assert "OMS/order/fill/settlement" in source or "OMS order/fill/settlement" in source

    assert "Safe RFP wording" in commercial
    assert "Unsafe RFP wording" in commercial
    assert "bank-specific certification" in commercial
    assert "Do not present quantified time savings" in commercial


def test_rfc0028_records_slice_eleven_runtime_security_and_latency_hardening() -> None:
    flat = _flat(RFC28_PATH)
    rfc_index = _flat(RFC_INDEX_PATH)
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH)
    commercial = _flat(COMMERCIAL_GUIDE_PATH)
    repo_context = _flat(REPO_CONTEXT_PATH)

    markers = (
        "src/core/bank_demo_proof/runtime_posture.py",
        "RuntimeEndpointEvidence",
        "latency_ms",
        "RFC0028_RUNTIME_SECURITY_POSTURE_HARDENED",
        "tests/unit/advisory/engine/test_engine_bank_demo_proof_models.py",
        "tests/unit/scripts/test_capture_rfc0028_backend_proof.py",
        "tests/unit/advisory/api/test_api_bank_demo_proof.py",
    )
    for marker in markers:
        assert marker in flat

    for source in (rfc_index, supported_features, repo_context):
        assert "runtime_posture.py" in source
        assert "latency_ms" in source
        assert "RFC0028_RUNTIME_SECURITY_POSTURE_HARDENED" in source
        assert "client-ready publication" in source
        assert "OMS/order/fill/settlement" in source or "OMS/order/fill/settlement" in (source)

    assert "bounded probe latency" in commercial
    assert "credentials, query strings, or fragments" in commercial
    assert "trace, and correlation fields" in commercial


def test_rfc0028_records_slice_twelve_documentation_product_truth() -> None:
    flat = _flat(RFC28_PATH)
    rfc_index = _flat(RFC_INDEX_PATH)
    wiki_index = _flat(WIKI_RFC_INDEX_PATH)
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH)
    readme = _flat(README_PATH)
    api_surface = _flat(WIKI_API_SURFACE_PATH)
    security = _flat(WIKI_SECURITY_PATH)
    operations = _flat(WIKI_OPERATIONS_PATH)

    rfc_markers = (
        "Slice 12 implementation decision and evidence",
        "README.md",
        "wiki/API-Surface.md",
        "wiki/Security-and-Governance.md",
        "wiki/Operations-Runbook.md",
        "RFC0028_RUNTIME_SECURITY_POSTURE_HARDENED",
        "tests/unit/test_rfc0028_gold_standard_tightening_contract.py",
    )
    for marker in rfc_markers:
        assert marker in flat

    readme_markers = (
        "/advisory/bank-demo-proof/proof-packs",
        "runtime-posture.json",
        "sanitized-runtime-summary.json",
        "latency_ms",
        "docs/commercial/RFC-0028-bank-demo-client-proof-materials.md",
        "HTTP 409",
        "client-ready publication",
        "OMS/order/fill/settlement",
    )
    for marker in readme_markers:
        assert marker in readme

    api_markers = (
        "GET /advisory/bank-demo-proof/scenario-contract",
        "GET /advisory/bank-demo-proof/supported-claim-register",
        "POST /advisory/bank-demo-proof/proof-packs",
        "HTTP 409",
        "latency_ms",
        "Gateway and Workbench",
        "OMS/order/fill/settlement",
    )
    for marker in api_markers:
        assert marker in api_surface

    security_markers = (
        "RFC-0028 Proof Artifact Governance",
        "credentials, query strings, or fragments",
        "secrets, tokens, prompts",
        "committed proof assets must use commit-safe or customer-consumable access classes",
        "`COMMIT_SOURCE` retention, and a canonical content hash",
        "bank-specific attestations",
        "OMS/order/fill/settlement",
    )
    for marker in security_markers:
        assert marker in security

    operations_markers = (
        "scripts/capture_rfc0028_backend_proof.py",
        "--run-live-suite",
        "proof-pack.json",
        "runtime-posture.json",
        "BANK_DEMO_PROOF_PACK_CREATED",
        "RFC0028_BACKEND_PROOF_MATERIAL_REVIEW_BLOCKED",
        "client-ready publication",
    )
    for marker in operations_markers:
        assert marker in operations

    for source in (rfc_index, wiki_index, supported_features):
        assert "Slice 12" in source
        assert "runtime posture" in source
        assert "HTTP 409" in source
        assert "client-ready publication" in source
        assert "OMS/order/fill/settlement" in source


def test_rfc0028_records_final_closure_artifact_hardening_and_communication() -> None:
    flat = _flat(RFC28_PATH)
    rfc_index = _flat(RFC_INDEX_PATH)
    wiki_index = _flat(WIKI_RFC_INDEX_PATH)
    supported_features = _flat(WIKI_SUPPORTED_FEATURES_PATH)
    readme = _flat(README_PATH)
    repo_context = _flat(REPO_CONTEXT_PATH)
    api_surface = _flat(WIKI_API_SURFACE_PATH)
    security = _flat(WIKI_SECURITY_PATH)
    operations = _flat(WIKI_OPERATIONS_PATH)
    commercial = _flat(COMMERCIAL_GUIDE_PATH)

    rfc_markers = (
        "IMPLEMENTED - BANK-DEMO PROOF AND CLAIM-CONTROLLED COMMERCIAL MATERIAL COMPLETE",
        "Slice 13 implementation decision and evidence",
        "Slice 14 hardening decision and evidence",
        "Slice 15 closure decision and evidence",
        "Slice 16 post-completion communication decision and evidence",
        "PR #213",
        "a99474e5457dcdd4c87e79faf83bc8f64580544b",
        "26573760885",
        "src/core/bank_demo_proof/artifact_refs.py",
        "HTTP 422 responses retain useful",
        "PR #369",
        "26d74e65e231ac3d62457187c6eb7f787a4d9f88",
        "26574820026",
        "LI-2026-05-28-043-demo-proof-should-show-the-boundary.md",
    )
    for marker in rfc_markers:
        assert marker in flat

    closure_sources = (
        rfc_index,
        wiki_index,
        supported_features,
        readme,
        repo_context,
        api_surface,
        security,
        operations,
        commercial,
    )
    for source in closure_sources:
        assert (
            "artifact_refs.py" in source
            or "proof artifact refs" in source
            or "proof artifact references" in source
            or "proof-artifact references" in source
            or "artifact references" in source
            or "artifact-reference" in source
        )
        assert "HTTP 422" in source
        assert "client-ready publication" in source
        assert "OMS/order/fill/settlement" in source

    for source in (readme, api_surface, security, operations, commercial):
        assert "token" in source
        assert "prompt" in source

    for source in (rfc_index, wiki_index, supported_features, readme, repo_context):
        assert "26573760885" in source
        assert "a99474e5457dcdd4c87e79faf83bc8f64580544b" in source
        assert "LI-2026-05-28-043-demo-proof-should-show-the-boundary.md" in source

    assert (
        "IMPLEMENTED - bank-demo proof and claim-controlled commercial material complete"
        in rfc_index
    )
    assert "RFC-0028 is implemented for repeatable bank-demo proof" in wiki_index
    assert "Implemented for source scenario contracts" in supported_features
    for source in (wiki_index, readme, repo_context):
        assert "PR #369" in source
        assert "26d74e65e231ac3d62457187c6eb7f787a4d9f88" in source
        assert "26574820026" in source


def test_rfc0028_supported_features_ledger_reflects_implemented_closure_truth() -> None:
    rfc = _read(RFC28_PATH)
    ledger = rfc.split("## 17. Supported-Features Ledger", maxsplit=1)[1].split(
        "Current implementation note:", maxsplit=1
    )[0]
    flat_ledger = " ".join(ledger.split())

    assert "Current support posture" in ledger
    assert "Initial RFC state" not in ledger
    assert "| Canonical advisory demo scenario | Supported |" in ledger
    assert "| Advisory bank demo proof pack | Supported |" in ledger
    assert "| Supported-claim register | Supported |" in ledger
    assert "| Gateway demo/proof integration | Supported |" in ledger
    assert (
        "| Workbench end-to-end demo journey | Supported for the governed canonical proof surface |"
    ) in ledger
    assert "| RFP/security pack | Supported for implementation-backed responses |" in ledger
    assert "| LinkedIn post-completion draft | Supported |" in ledger
    assert "client-ready publication, external communication, OMS/order/fill/settlement" in (
        flat_ledger
    )
    assert "bank-specific attestations remain blocked" in flat_ledger
    assert "| Proposed |" not in ledger


def test_rfc0028_closure_language_does_not_describe_completed_slices_as_later_work() -> None:
    flat = _flat(RFC28_PATH)

    stale_closure_phrases = (
        "later Gateway/Workbench",
        "later Gateway and Workbench",
        "unless a later owner-repo implementation",
        "combined with the later commercial",
    )
    for phrase in stale_closure_phrases:
        assert phrase not in flat
