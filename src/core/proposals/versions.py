from datetime import datetime
from typing import Any

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.models import ProposalResult
from src.core.proposals.models import ProposalVersionRecord


def build_proposal_version_record(
    *,
    proposal_version_id: str,
    proposal_id: str,
    version_no: int,
    request_hash: str,
    proposal_result: ProposalResult,
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    created_at: datetime,
    store_evidence_bundle: bool,
) -> ProposalVersionRecord:
    simulation_payload = proposal_result.model_dump(mode="json", warnings=False)
    simulation_hash_payload = strip_keys(
        simulation_payload,
        exclude={"correlation_id", "idempotency_key"},
    )
    simulation_hash = hash_canonical_payload(simulation_hash_payload)
    artifact_hash = artifact["evidence_bundle"]["hashes"]["artifact_hash"]
    return ProposalVersionRecord(
        proposal_version_id=proposal_version_id,
        proposal_id=proposal_id,
        version_no=version_no,
        created_at=created_at,
        request_hash=request_hash,
        artifact_hash=artifact_hash,
        simulation_hash=simulation_hash,
        status_at_creation=proposal_result.status,
        proposal_result_json=simulation_payload,
        artifact_json=artifact,
        evidence_bundle_json=evidence_bundle if store_evidence_bundle else {},
        gate_decision_json=(
            proposal_result.gate_decision.model_dump(mode="json")
            if proposal_result.gate_decision is not None
            else None
        ),
    )
