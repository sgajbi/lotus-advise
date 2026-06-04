from __future__ import annotations

from typing import Any

from src.core.advisory.artifact_models import ProposalArtifact
from src.core.advisory.narrative import build_deterministic_proposal_narrative
from src.core.advisory.narrative_envelope_models import ProposalNarrative
from src.core.advisory.narrative_request_models import ProposalNarrativeRequest
from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.narrative_review import (
    ProposalNarrativeReviewError,
    latest_narrative_review_record,
)
from src.core.proposals.persistence_models import (
    ProposalRecord,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.projections import to_proposal_summary
from src.core.proposals.response_models import (
    ProposalNarrativeReadResponse,
    ProposalNarrativeRegenerationRequest,
    ProposalNarrativeRegenerationResponse,
)


def build_narrative_read_response(
    *,
    proposal: ProposalRecord,
    version: ProposalVersionRecord,
    events: list[ProposalWorkflowEventRecord],
) -> ProposalNarrativeReadResponse:
    narrative_payload = _reviewable_narrative_payload(version)
    narrative = ProposalNarrative.model_validate(narrative_payload)
    review = latest_narrative_review_record(events=events, version=version)
    return ProposalNarrativeReadResponse(
        proposal=to_proposal_summary(proposal),
        proposal_version_no=version.version_no,
        proposal_version_id=version.proposal_version_id,
        proposal_narrative=narrative,
        narrative_review=review,
        source_narrative_hash=hash_canonical_payload(narrative_payload),
        replay_evidence_path=(
            f"/advisory/proposals/{proposal.proposal_id}/versions/"
            f"{version.version_no}/replay-evidence"
        ),
        read_posture={
            "source": "IMMUTABLE_PROPOSAL_VERSION_ARTIFACT",
            "mutation_performed": False,
            "client_ready_publication": "GATED",
        },
    )


def build_narrative_regeneration_response(
    *,
    proposal: ProposalRecord,
    version: ProposalVersionRecord,
    events: list[ProposalWorkflowEventRecord],
    payload: ProposalNarrativeRegenerationRequest,
) -> ProposalNarrativeRegenerationResponse:
    current_payload = _reviewable_narrative_payload(version)
    artifact = ProposalArtifact.model_validate(version.artifact_json)
    request = _regeneration_request_from_payload(
        current_payload=current_payload,
        payload=payload,
    )
    regenerated = build_deterministic_proposal_narrative(
        artifact=artifact,
        request=request,
    )
    regenerated_payload = regenerated.model_dump(mode="json")
    current_hash = hash_canonical_payload(current_payload)
    regenerated_hash = hash_canonical_payload(regenerated_payload)
    review = latest_narrative_review_record(events=events, version=version)
    return ProposalNarrativeRegenerationResponse(
        proposal=to_proposal_summary(proposal),
        proposal_version_no=version.version_no,
        proposal_version_id=version.proposal_version_id,
        current_narrative_id=str(current_payload["narrative_id"]),
        regenerated_narrative=regenerated,
        current_source_narrative_hash=current_hash,
        regenerated_source_narrative_hash=regenerated_hash,
        source_artifact_hash=version.artifact_hash,
        source_request_hash=version.request_hash,
        latest_narrative_review=review,
        materially_changed=current_hash != regenerated_hash,
        regeneration_posture={
            "source": "IMMUTABLE_PROPOSAL_VERSION_ARTIFACT",
            "persistence_status": "NOT_PERSISTED_REVIEW_REQUIRED",
            "mutation_performed": False,
            "client_ready_publication": "GATED",
            "review_required_before_report_package": True,
        },
    )


def _regeneration_request_from_payload(
    *,
    current_payload: dict[str, Any],
    payload: ProposalNarrativeRegenerationRequest,
) -> ProposalNarrativeRequest:
    current = ProposalNarrative.model_validate(current_payload)
    policy_context = current.narrative_policy.context
    current_sections = [section.section_key for section in current.sections]
    return ProposalNarrativeRequest(
        audience="ADVISOR_REVIEW",
        sections=payload.sections if payload.sections is not None else current_sections,
        requested_by=payload.requested_by,
        jurisdiction=payload.jurisdiction or policy_context.jurisdiction,
        product_types=payload.product_types
        if payload.product_types is not None
        else list(policy_context.product_types),
        client_audience=payload.client_audience,
        generation_mode=payload.generation_mode,
    )


def _reviewable_narrative_payload(version: ProposalVersionRecord) -> dict[str, Any]:
    narrative = version.artifact_json.get("proposal_narrative")
    if not isinstance(narrative, dict) or not narrative.get("narrative_id"):
        raise ProposalNarrativeReviewError("PROPOSAL_NARRATIVE_NOT_FOUND")
    return narrative
