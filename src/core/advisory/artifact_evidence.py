from typing import cast

from src.core.advisory.artifact_evidence_models import (
    ProposalArtifactEngineOutputs,
    ProposalArtifactEvidenceBundle,
    ProposalArtifactEvidenceInputs,
    ProposalArtifactHashes,
)
from src.core.advisory.artifact_models import ProposalArtifact
from src.core.advisory.narrative import build_deterministic_proposal_narrative
from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposal_result_models import ProposalResult


def build_artifact_evidence_bundle(
    *, request: ProposalSimulateRequest, proposal_result: ProposalResult
) -> ProposalArtifactEvidenceBundle:
    return ProposalArtifactEvidenceBundle(
        inputs=ProposalArtifactEvidenceInputs(
            portfolio_snapshot=request.portfolio_snapshot.model_dump(mode="json"),
            market_data_snapshot=request.market_data_snapshot.model_dump(mode="json"),
            shelf_entries=[entry.model_dump(mode="json") for entry in request.shelf_entries],
            options=request.options.model_dump(mode="json"),
            proposed_cash_flows=[
                item.model_dump(mode="json") for item in request.proposed_cash_flows
            ],
            proposed_trades=[item.model_dump(mode="json") for item in request.proposed_trades],
            reference_model=(
                request.reference_model.model_dump(mode="json")
                if request.reference_model is not None
                else None
            ),
        ),
        engine_outputs=ProposalArtifactEngineOutputs(
            proposal_result=proposal_result.model_dump(mode="json")
        ),
        hashes=ProposalArtifactHashes(
            request_hash=proposal_result.lineage.request_hash,
            artifact_hash="",
        ),
        engine_version=proposal_result.lineage.engine_version or "unknown",
    )


def finalize_artifact_evidence_hashes(
    *, artifact: ProposalArtifact, request: ProposalSimulateRequest
) -> ProposalArtifact:
    payload = artifact.model_dump(mode="json")
    base_canonical_payload = strip_keys(
        payload, exclude={"created_at", "artifact_hash", "proposal_narrative"}
    )
    payload["evidence_bundle"]["hashes"]["artifact_hash"] = hash_canonical_payload(
        base_canonical_payload
    )
    artifact = ProposalArtifact.model_validate(payload)

    if request.narrative_request is not None:
        narrative = build_deterministic_proposal_narrative(
            artifact=artifact,
            request=request.narrative_request,
        )
        payload = artifact.model_dump(mode="json")
        payload["proposal_narrative"] = narrative.model_dump(mode="json")
        narrative_canonical_payload = strip_keys(payload, exclude={"created_at", "artifact_hash"})
        payload["evidence_bundle"]["hashes"]["artifact_hash"] = hash_canonical_payload(
            narrative_canonical_payload
        )

    return cast(ProposalArtifact, ProposalArtifact.model_validate(payload))
