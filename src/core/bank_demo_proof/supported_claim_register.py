from __future__ import annotations

from src.core.bank_demo_proof.models import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
    AdvisorySupportedClaimRegister,
    ArtifactPolicy,
    SupportedClaim,
    SupportedClaimProofRequirement,
)

RFC28_SUPPORTED_CLAIM_REGISTER_REF = "lotus-advise://rfc0028/supported-claim-register.v1.json"


def build_default_supported_claim_register() -> AdvisorySupportedClaimRegister:
    backend_summary_ref = "proof.assets.sanitized_runtime_summary"
    document_proof_ref = "proof.assets.document_proof_summary"
    integration_proof_ref = "proof.assets.journey_integration_proof_summary"
    commercial_material_ref = "proof.assets.commercial_material_pack"
    field_review_ref = "proof.assets.material_field_review"
    runtime_posture_ref = "proof.assets.runtime_posture"
    return AdvisorySupportedClaimRegister(
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        artifact_policy=ArtifactPolicy(
            commit_allowed_access_classes=[
                "COMMIT_SAFE_SUMMARY",
                "CUSTOMER_CONSUMABLE_SUMMARY",
            ],
            local_only_access_classes=[
                "LOCAL_ONLY_RUNTIME_EVIDENCE",
                "SECRET_MATERIAL",
            ],
            sensitive_material_rules=[
                "Secrets, tokens, prompts, raw provider payloads, and raw runtime logs stay local "
                "and must not be committed or used in client-facing proof material.",
            ],
        ),
        claims=[
            SupportedClaim(
                claim_id="backend_proof_capture_repeatable",
                title="Repeatable backend proof capture",
                classification="IMPLEMENTATION_BACKED",
                audiences=["DEVELOPER", "OPERATIONS", "PRE_SALES"],
                allowed_materials=["README", "WIKI", "OPERATOR_RUNBOOK"],
                claim_text=(
                    "lotus-advise can generate a sanitized RFC-0028 backend proof pack from the "
                    "governed live runtime suite for the canonical private-banking scenario."
                ),
                evidence_refs=[backend_summary_ref, field_review_ref, runtime_posture_ref],
                proof_requirements=[
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-live-runtime-suite-result",
                        evidence_ref=backend_summary_ref,
                    ),
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-material-field-review",
                        evidence_ref=field_review_ref,
                    ),
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-runtime-posture",
                        evidence_ref=runtime_posture_ref,
                    ),
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-document-proof-summary",
                        evidence_ref=document_proof_ref,
                    ),
                ],
                wording_rules=[
                    "State that this is backend proof until Gateway and Workbench slices pass.",
                    "Do not imply client-ready approval or external client communication.",
                ],
            ),
            SupportedClaim(
                claim_id="advisor_journey_backend_evidence_available",
                title="Advisor journey backend evidence available",
                classification="BACKEND_BACKED_UI_PENDING",
                audiences=["BUSINESS_USER", "SALES", "PRE_SALES", "CLIENT_DEMO"],
                allowed_materials=["WIKI", "DEMO_SCRIPT"],
                claim_text=(
                    "The advisory backend can prove the advisor journey evidence for proposal "
                    "lifecycle, narrative, memo, policy, report seam, and execution boundary "
                    "review before product-surface promotion."
                ),
                evidence_refs=[backend_summary_ref, field_review_ref],
                proof_requirements=[
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-backend-advisor-journey-review",
                        evidence_ref=field_review_ref,
                    )
                ],
                wording_rules=[
                    "Use 'backend evidence available' until Gateway and Workbench proof is merged.",
                    "Do not use screenshots for this claim in Slice 5.",
                ],
            ),
            SupportedClaim(
                claim_id="advisor_use_document_proof_available",
                title="Advisor-use document proof is available",
                classification="BACKEND_BACKED_UI_PENDING",
                audiences=["BUSINESS_USER", "SALES", "PRE_SALES", "CLIENT_DEMO"],
                allowed_materials=["WIKI", "DEMO_SCRIPT"],
                claim_text=(
                    "The advisory backend records advisor-use memo and policy report packages "
                    "with render, archive, retention, legal-hold, and access-audit posture while "
                    "keeping client-ready documents blocked."
                ),
                evidence_refs=[document_proof_ref, field_review_ref],
                proof_requirements=[
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-advisor-use-document-proof",
                        evidence_ref=document_proof_ref,
                    )
                ],
                wording_rules=[
                    "Use advisor-use document wording only until product-surface proof passes.",
                    "Do not imply client-ready publication or external client distribution.",
                ],
            ),
            SupportedClaim(
                claim_id="degraded_runtime_boundary_evidence_available",
                title="Degraded runtime boundaries are evidence-backed",
                classification="DEGRADED_SUPPORTED",
                audiences=["DEVELOPER", "OPERATIONS", "PRE_SALES"],
                allowed_materials=["WIKI", "OPERATOR_RUNBOOK"],
                claim_text=(
                    "RFC-0028 backend proof records lotus-risk and lotus-core degraded paths and "
                    "keeps unsupported client-ready claims blocked when source evidence is absent."
                ),
                evidence_refs=[field_review_ref],
                proof_requirements=[
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-degraded-source-review",
                        evidence_ref=field_review_ref,
                    )
                ],
                wording_rules=[
                    "Describe degraded support as controlled evidence posture, not as approval.",
                ],
            ),
            SupportedClaim(
                claim_id="ai_policy_cockpit_proof_integrated",
                title="AI, policy, and cockpit proof boundaries are integrated",
                classification="IMPLEMENTATION_BACKED",
                audiences=["DEVELOPER", "OPERATIONS", "PRE_SALES"],
                allowed_materials=["README", "WIKI", "OPERATOR_RUNBOOK"],
                claim_text=(
                    "RFC-0028 backend proof includes a sanitized integration summary for "
                    "governed AI/model-risk controls, policy evidence, and advisor-cockpit "
                    "product-surface boundaries without promoting AI authority, policy approval, "
                    "or client-ready publication."
                ),
                evidence_refs=[integration_proof_ref, field_review_ref],
                proof_requirements=[
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-ai-policy-cockpit-integration-proof",
                        evidence_ref=integration_proof_ref,
                    ),
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-ai-policy-cockpit-material-review",
                        evidence_ref=field_review_ref,
                    ),
                ],
                wording_rules=[
                    "State that AI is review-gated and non-authoritative.",
                    (
                        "State that policy examples are source-owned reference controls, "
                        "not legal advice."
                    ),
                    "Do not imply advisor acknowledgement clears policy blockers.",
                ],
            ),
            SupportedClaim(
                claim_id="client_ready_publication_blocked",
                title="Client-ready publication is blocked",
                classification="UNSUPPORTED",
                audiences=["DEVELOPER", "OPERATIONS", "SALES", "PRE_SALES"],
                allowed_materials=["WIKI", "OPERATOR_RUNBOOK"],
                claim_text=(
                    "Client-ready publication, sign-off approval, and external client "
                    "communication are not supported by this backend proof slice."
                ),
                wording_rules=[
                    "Use blocked/not supported language in all RFC-0028 Slice 5 material.",
                ],
            ),
            SupportedClaim(
                claim_id="commercial_rfp_security_material_available",
                title="Commercial, RFP, security, architecture, ROI, and demo material available",
                classification="IMPLEMENTATION_BACKED",
                audiences=[
                    "DEVELOPER",
                    "OPERATIONS",
                    "SALES",
                    "PRE_SALES",
                    "CLIENT_DEMO",
                    "RFP_SECURITY",
                ],
                allowed_materials=[
                    "README",
                    "WIKI",
                    "SUPPORTED_FEATURES",
                    "DEMO_SCRIPT",
                    "PRODUCT_ONE_PAGER",
                    "RFP_RESPONSE",
                    "SECURITY_PACK",
                    "ARCHITECTURE_DECK",
                    "ROI_STORY",
                    "OPERATOR_RUNBOOK",
                ],
                claim_text=(
                    "RFC-0028 has claim-controlled product one-pager, RFP response, security "
                    "posture, architecture, demo-script, proof-guide, ROI, feature-matrix, "
                    "client-demo boundary, and operator-checklist material grounded in the "
                    "supported-claim register and sanitized proof pack."
                ),
                evidence_refs=[commercial_material_ref, field_review_ref],
                proof_requirements=[
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-commercial-material-pack",
                        evidence_ref=commercial_material_ref,
                    ),
                    SupportedClaimProofRequirement(
                        requirement_id="rfc0028-commercial-material-field-review",
                        evidence_ref=field_review_ref,
                    ),
                ],
                wording_rules=[
                    "Map every asset to the supported-claim register before use.",
                    "Do not claim bank-specific certifications or external attestations.",
                    (
                        "Do not claim client-ready publication, policy approval, "
                        "or execution authority."
                    ),
                ],
            ),
            SupportedClaim(
                claim_id="rfp_security_package_pending",
                title="Legacy RFP and security pack pending claim is retired",
                classification="UNSUPPORTED",
                audiences=["DEVELOPER", "OPERATIONS"],
                allowed_materials=["WIKI", "OPERATOR_RUNBOOK"],
                claim_text=(
                    "The old pending RFP/security wording is retired. Use "
                    "commercial_rfp_security_material_available for the implemented, "
                    "claim-controlled material pack and preserve the blocked boundaries."
                ),
                wording_rules=[
                    "Do not use this retired claim in product, RFP, security, or demo material.",
                ],
            ),
        ],
    )
