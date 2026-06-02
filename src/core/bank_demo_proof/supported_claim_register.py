from __future__ import annotations

from src.core.bank_demo_proof.model_common import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
)
from src.core.bank_demo_proof.supported_claim_backend_evidence import (
    build_backend_evidence_supported_claims,
)
from src.core.bank_demo_proof.supported_claim_boundaries import (
    build_boundary_supported_claims,
)
from src.core.bank_demo_proof.supported_claim_models import AdvisorySupportedClaimRegister
from src.core.bank_demo_proof.supported_claim_policy import build_supported_claim_artifact_policy
from src.core.bank_demo_proof.supported_claim_product_surface import (
    build_product_surface_supported_claims,
)
from src.core.bank_demo_proof.supported_claim_refs import RFC28_SUPPORTED_CLAIM_REGISTER_REF

__all__ = [
    "RFC28_SUPPORTED_CLAIM_REGISTER_REF",
    "build_default_supported_claim_register",
]


def build_default_supported_claim_register() -> AdvisorySupportedClaimRegister:
    return AdvisorySupportedClaimRegister(
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        artifact_policy=build_supported_claim_artifact_policy(),
        claims=[
            *build_backend_evidence_supported_claims(),
            *build_product_surface_supported_claims(),
            *build_boundary_supported_claims(),
        ],
    )
