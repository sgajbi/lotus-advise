from typing import Any, cast

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
        inputs=_build_evidence_inputs(request),
        engine_outputs=ProposalArtifactEngineOutputs(
            proposal_result=proposal_result.model_dump(mode="json")
        ),
        hashes=ProposalArtifactHashes(
            request_hash=proposal_result.lineage.request_hash,
            artifact_hash="",
        ),
        engine_version=proposal_result.lineage.engine_version or "unknown",
    )


def _build_evidence_inputs(request: ProposalSimulateRequest) -> ProposalArtifactEvidenceInputs:
    return ProposalArtifactEvidenceInputs(
        portfolio_snapshot=request.portfolio_snapshot.model_dump(mode="json"),
        market_data_snapshot=request.market_data_snapshot.model_dump(mode="json"),
        shelf_entries=_dump_model_list(request.shelf_entries),
        options=request.options.model_dump(mode="json"),
        proposed_cash_flows=_dump_model_list(request.proposed_cash_flows),
        proposed_trades=_dump_model_list(request.proposed_trades),
        reference_model=_dump_optional_model(request.reference_model),
    )


def _dump_model_list(items: list[Any]) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in items]


def _dump_optional_model(item: Any | None) -> dict[str, Any] | None:
    if item is None:
        return None
    return cast(dict[str, Any], item.model_dump(mode="json"))


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
