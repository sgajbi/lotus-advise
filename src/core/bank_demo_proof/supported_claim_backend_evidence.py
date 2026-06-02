from __future__ import annotations

from src.core.bank_demo_proof.supported_claim_models import (
    SupportedClaim,
    SupportedClaimProofRequirement,
)
from src.core.bank_demo_proof.supported_claim_refs import (
    BACKEND_SUMMARY_REF,
    DOCUMENT_PROOF_REF,
    FIELD_REVIEW_REF,
    RUNTIME_POSTURE_REF,
)


def build_backend_evidence_supported_claims() -> list[SupportedClaim]:
    return [
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
            evidence_refs=[
                BACKEND_SUMMARY_REF,
                DOCUMENT_PROOF_REF,
                FIELD_REVIEW_REF,
                RUNTIME_POSTURE_REF,
            ],
            proof_requirements=[
                SupportedClaimProofRequirement(
                    requirement_id="rfc0028-live-runtime-suite-result",
                    evidence_ref=BACKEND_SUMMARY_REF,
                ),
                SupportedClaimProofRequirement(
                    requirement_id="rfc0028-material-field-review",
                    evidence_ref=FIELD_REVIEW_REF,
                ),
                SupportedClaimProofRequirement(
                    requirement_id="rfc0028-runtime-posture",
                    evidence_ref=RUNTIME_POSTURE_REF,
                ),
                SupportedClaimProofRequirement(
                    requirement_id="rfc0028-document-proof-summary",
                    evidence_ref=DOCUMENT_PROOF_REF,
                ),
            ],
            wording_rules=[
                (
                    "State when material is limited to backend proof and route "
                    "product-surface claims through the product-surface proof claim."
                ),
                "Do not imply client-ready approval or external client communication.",
            ],
        ),
        SupportedClaim(
            claim_id="advisor_journey_backend_evidence_available",
            title="Advisor journey backend evidence available",
            classification="IMPLEMENTATION_BACKED",
            audiences=["DEVELOPER", "OPERATIONS", "PRE_SALES"],
            allowed_materials=["WIKI", "OPERATOR_RUNBOOK"],
            claim_text=(
                "The advisory backend can prove the advisor journey evidence for proposal "
                "lifecycle, narrative, memo, policy, report-package handoff, and execution "
                "boundary review as internal implementation evidence."
            ),
            evidence_refs=[BACKEND_SUMMARY_REF, FIELD_REVIEW_REF],
            proof_requirements=[
                SupportedClaimProofRequirement(
                    requirement_id="rfc0028-backend-advisor-journey-review",
                    evidence_ref=FIELD_REVIEW_REF,
                )
            ],
            wording_rules=[
                "Use backend-evidence wording only for internal or operator material.",
                (
                    "Use advisor_journey_product_surface_proven for client-demo, product, "
                    "and commercial journey material."
                ),
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
            evidence_refs=[FIELD_REVIEW_REF],
            proof_requirements=[
                SupportedClaimProofRequirement(
                    requirement_id="rfc0028-degraded-source-review",
                    evidence_ref=FIELD_REVIEW_REF,
                )
            ],
            wording_rules=[
                "Describe degraded support as controlled evidence posture, not as approval.",
            ],
        ),
    ]
