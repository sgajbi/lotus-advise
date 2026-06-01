from copy import deepcopy
from typing import Any, cast

from src.core.advisory.risk_lens import extract_risk_lens
from src.core.proposal_result_models import ProposalResult
from src.core.proposals.memo_source_readiness import build_memo_source_readiness
from src.core.proposals.policy_source_readiness import build_policy_source_readiness


def build_proposal_evidence_bundle(
    *,
    artifact_evidence_bundle: Any,
    proposal_result: ProposalResult,
    context_resolution: dict[str, Any],
    context_resolution_override: dict[str, Any] | None = None,
    replay_lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence_bundle = cast(dict[str, Any], artifact_evidence_bundle.model_dump(mode="json"))
    evidence_bundle["context_resolution"] = (
        deepcopy(context_resolution_override)
        if context_resolution_override is not None
        else deepcopy(context_resolution)
    )
    evidence_bundle["risk_lens"] = extract_risk_lens(proposal_result)
    evidence_bundle["memo_source_readiness"] = build_memo_source_readiness(evidence_bundle)
    evidence_bundle["policy_source_readiness"] = build_policy_source_readiness(evidence_bundle)
    if replay_lineage:
        evidence_bundle["replay_lineage"] = deepcopy(replay_lineage)
    return evidence_bundle
