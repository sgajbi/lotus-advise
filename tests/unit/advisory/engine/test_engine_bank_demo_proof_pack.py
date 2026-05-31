from __future__ import annotations

from datetime import UTC, datetime

from src.core.bank_demo_proof import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
    ProofAsset,
    build_backend_proof_pack,
)
from src.core.bank_demo_proof.proof_pack import RFC28_BACKEND_PROOF_EVIDENCE_MARKERS
from src.core.bank_demo_proof.scenario_contract import (
    RFC28_SCENARIO_CONTRACT_REF,
    RFC28_SOURCE_PRODUCT_REFS,
    RFC28_UNSUPPORTED_BOUNDARIES,
)
from src.core.bank_demo_proof.supported_claim_register import (
    RFC28_SUPPORTED_CLAIM_REGISTER_REF,
)


def _proof_asset() -> ProofAsset:
    return ProofAsset(
        asset_id="commercial_material_pack",
        asset_type="COMMERCIAL_DOCUMENT",
        source_repository="lotus-advise",
        uri="output/rfc0028/backend-proof/commercial-material-pack.json",
        access_class="CUSTOMER_CONSUMABLE_SUMMARY",
        retention_class="COMMIT_SOURCE",
        evidence_refs=["commercial_rfp_security_material_available"],
        content_hash=f"sha256:{'0' * 64}",
        commit_allowed=True,
    )


def test_backend_proof_pack_pins_canonical_contract_refs_and_markers() -> None:
    generated_at = datetime(2026, 5, 28, 9, 30, tzinfo=UTC)

    proof_pack = build_backend_proof_pack(
        generated_at=generated_at,
        correlation_id="corr-rfc0028-proof-pack",
        repository_sha="abc123",
        assets=[_proof_asset()],
    )

    assert proof_pack.proof_pack_id == "rfc0028-backend-proof-20260528T093000Z"
    assert proof_pack.scenario_id == RFC28_CANONICAL_SCENARIO_ID
    assert proof_pack.primary_portfolio_id == RFC28_CANONICAL_PORTFOLIO_ID
    assert proof_pack.proof_marker == RFC28_CANONICAL_PROOF_MARKER
    assert proof_pack.client_ready_posture == "CLIENT_READY_PUBLICATION_BLOCKED"
    assert proof_pack.repository_shas == {"lotus-advise": "abc123"}
    assert proof_pack.evidence_markers == list(RFC28_BACKEND_PROOF_EVIDENCE_MARKERS)
    assert proof_pack.scenario_contract_ref == RFC28_SCENARIO_CONTRACT_REF
    assert proof_pack.supported_claim_register_ref == RFC28_SUPPORTED_CLAIM_REGISTER_REF
    assert proof_pack.source_product_refs == list(RFC28_SOURCE_PRODUCT_REFS)
    assert proof_pack.unsupported_boundaries == list(RFC28_UNSUPPORTED_BOUNDARIES)


def test_backend_proof_pack_never_promotes_client_ready_or_execution_scope() -> None:
    proof_pack = build_backend_proof_pack(
        generated_at=datetime(2026, 5, 28, 9, 30, tzinfo=UTC),
        correlation_id="corr-rfc0028-proof-pack",
        repository_sha="abc123",
        assets=[_proof_asset()],
    )

    blocked_scope = " ".join(proof_pack.unsupported_boundaries).lower()

    assert proof_pack.client_ready_posture == "CLIENT_READY_PUBLICATION_BLOCKED"
    assert "client-ready publication remains blocked" in blocked_scope
    assert "external client communication" in blocked_scope
    assert "oms order, fill, settlement" in blocked_scope
