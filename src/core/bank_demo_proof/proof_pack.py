from __future__ import annotations

from datetime import datetime

from src.core.bank_demo_proof.model_common import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
)
from src.core.bank_demo_proof.proof_asset_models import ProofAsset
from src.core.bank_demo_proof.proof_pack_models import AdvisoryBankDemoProofPack
from src.core.bank_demo_proof.scenario_contract import (
    RFC28_SCENARIO_CONTRACT_REF,
    RFC28_SOURCE_PRODUCT_REFS,
    RFC28_UNSUPPORTED_BOUNDARIES,
)
from src.core.bank_demo_proof.supported_claim_register import (
    RFC28_SUPPORTED_CLAIM_REGISTER_REF,
)

RFC28_BACKEND_PROOF_EVIDENCE_MARKERS: tuple[str, ...] = (
    RFC28_CANONICAL_PROOF_MARKER,
    "RFC0028_BACKEND_MATERIAL_FIELD_REVIEW_PASSED",
    "RFC0028_DOCUMENT_PROOF_SUMMARY_CREATED",
    "RFC0028_JOURNEY_INTEGRATION_PROOF_CREATED",
    "RFC0028_COMMERCIAL_MATERIAL_PACK_CREATED",
    "RFC0028_RUNTIME_POSTURE_CAPTURED",
    "RFC0028_RUNTIME_SECURITY_POSTURE_HARDENED",
)


def build_backend_proof_pack(
    *,
    generated_at: datetime,
    correlation_id: str,
    repository_sha: str,
    assets: list[ProofAsset],
) -> AdvisoryBankDemoProofPack:
    return AdvisoryBankDemoProofPack(
        proof_pack_id=f"rfc0028-backend-proof-{generated_at.strftime('%Y%m%dT%H%M%SZ')}",
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        generated_at=generated_at,
        correlation_id=correlation_id,
        client_ready_posture="CLIENT_READY_PUBLICATION_BLOCKED",
        repository_shas={"lotus-advise": repository_sha},
        evidence_markers=list(RFC28_BACKEND_PROOF_EVIDENCE_MARKERS),
        scenario_contract_ref=RFC28_SCENARIO_CONTRACT_REF,
        supported_claim_register_ref=RFC28_SUPPORTED_CLAIM_REGISTER_REF,
        source_product_refs=list(RFC28_SOURCE_PRODUCT_REFS),
        unsupported_boundaries=list(RFC28_UNSUPPORTED_BOUNDARIES),
        assets=assets,
    )
