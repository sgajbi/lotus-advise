from __future__ import annotations

from src.core.bank_demo_proof.supported_claim_models import (
    SupportedClaim,
    SupportedClaimProofRequirement,
)
from src.core.bank_demo_proof.supported_claim_refs import (
    BACKEND_SUMMARY_REF,
    COMMERCIAL_MATERIAL_REF,
    DOCUMENT_PROOF_REF,
    FIELD_REVIEW_REF,
    INTEGRATION_PROOF_REF,
)


def build_product_surface_supported_claims() -> list[SupportedClaim]:
    return [
        SupportedClaim(
            claim_id="advisor_journey_product_surface_proven",
            title="Advisor journey product surface is proven",
            classification="IMPLEMENTATION_BACKED",
            audiences=["BUSINESS_USER", "OPERATIONS", "SALES", "PRE_SALES", "CLIENT_DEMO"],
            allowed_materials=[
                "README",
                "WIKI",
                "SUPPORTED_FEATURES",
                "DEMO_SCRIPT",
                "PRODUCT_ONE_PAGER",
                "ARCHITECTURE_DECK",
                "ROI_STORY",
                "OPERATOR_RUNBOOK",
            ],
            claim_text=(
                "The canonical private-banking advisory proof journey is backed by Advise, "
                "Gateway, and Workbench evidence for the governed bank-demo proof surface."
            ),
            evidence_refs=[BACKEND_SUMMARY_REF, INTEGRATION_PROOF_REF, FIELD_REVIEW_REF],
            proof_requirements=[
                SupportedClaimProofRequirement(
                    requirement_id="rfc0028-advisor-journey-runtime-proof",
                    evidence_ref=BACKEND_SUMMARY_REF,
                ),
                SupportedClaimProofRequirement(
                    requirement_id="rfc0028-advisor-journey-product-surface-proof",
                    evidence_ref=INTEGRATION_PROOF_REF,
                ),
                SupportedClaimProofRequirement(
                    requirement_id="rfc0028-advisor-journey-material-review",
                    evidence_ref=FIELD_REVIEW_REF,
                ),
            ],
            wording_rules=[
                "State that the proof surface is governed and Gateway-backed.",
                "Do not imply client-ready publication or external client communication.",
                (
                    "Do not imply Workbench calculates advisory, policy, memo, narrative, "
                    "or AI truth."
                ),
            ],
        ),
        SupportedClaim(
            claim_id="advisor_use_document_proof_available",
            title="Advisor-use document proof is available",
            classification="IMPLEMENTATION_BACKED",
            audiences=["BUSINESS_USER", "SALES", "PRE_SALES", "CLIENT_DEMO"],
            allowed_materials=["WIKI", "DEMO_SCRIPT"],
            claim_text=(
                "The advisory backend records advisor-use memo and policy report packages "
                "with render, archive, retention, legal-hold, and access-audit posture while "
                "keeping client-ready documents blocked."
            ),
            evidence_refs=[DOCUMENT_PROOF_REF, FIELD_REVIEW_REF],
            proof_requirements=[
                SupportedClaimProofRequirement(
                    requirement_id="rfc0028-advisor-use-document-proof",
                    evidence_ref=DOCUMENT_PROOF_REF,
                )
            ],
            wording_rules=[
                "Use advisor-use document wording and keep client-ready publication blocked.",
                "Do not imply client-ready publication or external client distribution.",
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
            evidence_refs=[COMMERCIAL_MATERIAL_REF, FIELD_REVIEW_REF],
            proof_requirements=[
                SupportedClaimProofRequirement(
                    requirement_id="rfc0028-commercial-material-pack",
                    evidence_ref=COMMERCIAL_MATERIAL_REF,
                ),
                SupportedClaimProofRequirement(
                    requirement_id="rfc0028-commercial-material-field-review",
                    evidence_ref=FIELD_REVIEW_REF,
                ),
            ],
            wording_rules=[
                "Map every asset to the supported-claim register before use.",
                "Do not claim bank-specific certifications or external attestations.",
                ("Do not claim client-ready publication, policy approval, or execution authority."),
            ],
        ),
    ]
