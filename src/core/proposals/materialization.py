from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.core.advisory.artifact import build_proposal_artifact
from src.core.advisory.artifact_models import ProposalArtifact
from src.core.models import ProposalResult, ProposalSimulateRequest
from src.core.proposals.evidence import build_proposal_evidence_bundle


@dataclass(frozen=True)
class ProposalVersionMaterialization:
    artifact: ProposalArtifact
    evidence_bundle: dict[str, Any]


def build_proposal_version_materialization(
    *,
    request: ProposalSimulateRequest,
    proposal_result: ProposalResult,
    created_at: datetime,
    context_resolution: dict[str, Any],
    context_resolution_override: dict[str, Any] | None = None,
    replay_lineage: dict[str, Any] | None = None,
) -> ProposalVersionMaterialization:
    artifact = build_proposal_artifact(
        request=request,
        proposal_result=proposal_result,
        created_at=created_at.isoformat(),
    )
    evidence_bundle = build_proposal_evidence_bundle(
        artifact_evidence_bundle=artifact.evidence_bundle,
        proposal_result=proposal_result,
        context_resolution=context_resolution,
        context_resolution_override=context_resolution_override,
        replay_lineage=replay_lineage,
    )
    return ProposalVersionMaterialization(
        artifact=artifact,
        evidence_bundle=evidence_bundle,
    )
