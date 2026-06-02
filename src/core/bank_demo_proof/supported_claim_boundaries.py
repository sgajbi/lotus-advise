from __future__ import annotations

from src.core.bank_demo_proof.supported_claim_models import (
    SupportedClaim,
    SupportedClaimProofRequirement,
)
from src.core.bank_demo_proof.supported_claim_refs import (
    FIELD_REVIEW_REF,
    INTEGRATION_PROOF_REF,
)


def build_boundary_supported_claims() -> list[SupportedClaim]:
    return [
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
            evidence_refs=[INTEGRATION_PROOF_REF, FIELD_REVIEW_REF],
            proof_requirements=[
                SupportedClaimProofRequirement(
                    requirement_id="rfc0028-ai-policy-cockpit-integration-proof",
                    evidence_ref=INTEGRATION_PROOF_REF,
                ),
                SupportedClaimProofRequirement(
                    requirement_id="rfc0028-ai-policy-cockpit-material-review",
                    evidence_ref=FIELD_REVIEW_REF,
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
                "communication are not supported by this backend proof scope."
            ),
            wording_rules=[
                "Use blocked/not supported language in all RFC-0028 proof material.",
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
    ]
