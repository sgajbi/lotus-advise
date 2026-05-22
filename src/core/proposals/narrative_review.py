from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, cast

from src.core.advisory.narrative_models import (
    ProposalNarrativeClientReadyStatus,
    ProposalNarrativeReviewAction,
    ProposalNarrativeReviewedState,
    ProposalNarrativeReviewRecord,
    ProposalNarrativeReviewRequest,
)
from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.models import (
    ProposalNarrativeReviewResponse,
    ProposalRecord,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.projections import to_proposal_summary, to_workflow_event
from src.core.proposals.repository import ProposalRepository


class ProposalNarrativeReviewError(ValueError):
    pass


def build_narrative_review_request_hash(
    *,
    version: ProposalVersionRecord,
    payload: ProposalNarrativeReviewRequest,
) -> str:
    return cast(
        str,
        hash_canonical_payload(
            {
                "proposal_id": version.proposal_id,
                "proposal_version_no": version.version_no,
                "narrative_id": _narrative_id(version),
                "payload": payload.model_dump(mode="json"),
            }
        ),
    )


def record_narrative_review_event(
    *,
    repository: ProposalRepository,
    event_id: str,
    proposal: ProposalRecord,
    version: ProposalVersionRecord,
    payload: ProposalNarrativeReviewRequest,
    idempotency_key: str | None,
    occurred_at: datetime,
) -> ProposalNarrativeReviewResponse:
    _require_reviewable_narrative(version)
    request_hash = build_narrative_review_request_hash(version=version, payload=payload)
    replay_event = _find_replayed_review_event(
        repository=repository,
        proposal_id=proposal.proposal_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    if replay_event is not None:
        return _build_response(
            proposal=proposal,
            version=version,
            event=replay_event,
            replayed=True,
        )

    event = _build_review_event(
        event_id=event_id,
        proposal=proposal,
        version=version,
        payload=payload,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        occurred_at=occurred_at,
    )
    reviewed_proposal = proposal.model_copy(update={"last_event_at": occurred_at})
    result = repository.transition_proposal(
        proposal=reviewed_proposal,
        event=event,
        approval=None,
    )
    return _build_response(
        proposal=result.proposal,
        version=version,
        event=result.event,
        replayed=False,
    )


def latest_narrative_review_record(
    *,
    events: list[ProposalWorkflowEventRecord],
    version: ProposalVersionRecord,
) -> ProposalNarrativeReviewRecord | None:
    try:
        narrative_id = _narrative_id(version)
    except ProposalNarrativeReviewError:
        return None
    for event in reversed(events):
        if event.event_type != "NARRATIVE_REVIEWED":
            continue
        if event.related_version_no != version.version_no:
            continue
        if event.reason_json.get("narrative_id") != narrative_id:
            continue
        return _record_from_event(event=event, replayed=False)
    return None


def _find_replayed_review_event(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    idempotency_key: str | None,
    request_hash: str,
) -> ProposalWorkflowEventRecord | None:
    if not idempotency_key:
        return None
    for event in reversed(repository.list_events(proposal_id=proposal_id)):
        if event.event_type != "NARRATIVE_REVIEWED":
            continue
        if event.reason_json.get("idempotency_key") != idempotency_key:
            continue
        existing_hash = event.reason_json.get("idempotency_request_hash")
        if existing_hash is not None and existing_hash != request_hash:
            raise ProposalNarrativeReviewError("IDEMPOTENCY_KEY_CONFLICT: request hash mismatch")
        return event
    return None


def _build_review_event(
    *,
    event_id: str,
    proposal: ProposalRecord,
    version: ProposalVersionRecord,
    payload: ProposalNarrativeReviewRequest,
    idempotency_key: str | None,
    request_hash: str,
    occurred_at: datetime,
) -> ProposalWorkflowEventRecord:
    narrative = _narrative(version)
    review_state = _review_state(payload.action)
    client_ready_status = _client_ready_status(payload=payload, narrative=narrative)
    reason_json: dict[str, Any] = {
        "review_action": payload.action,
        "review_state": review_state,
        "client_ready_status": client_ready_status,
        "reason": payload.reason,
        "narrative_id": narrative["narrative_id"],
        "source_narrative_hash": hash_canonical_payload(narrative),
        "client_ready_release_requested": payload.client_ready_release_requested,
        "replacement_narrative_id": payload.replacement_narrative_id,
    }
    if idempotency_key:
        reason_json["idempotency_key"] = idempotency_key
        reason_json["idempotency_request_hash"] = request_hash
    return ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id=proposal.proposal_id,
        event_type="NARRATIVE_REVIEWED",
        from_state=proposal.current_state,
        to_state=proposal.current_state,
        actor_id=payload.reviewed_by,
        occurred_at=occurred_at,
        reason_json=reason_json,
        related_version_no=version.version_no,
    )


def _build_response(
    *,
    proposal: ProposalRecord,
    version: ProposalVersionRecord,
    event: ProposalWorkflowEventRecord,
    replayed: bool,
) -> ProposalNarrativeReviewResponse:
    return ProposalNarrativeReviewResponse(
        proposal=to_proposal_summary(proposal),
        narrative_review=_record_from_event(event=event, replayed=replayed),
        latest_workflow_event=to_workflow_event(event),
    )


def _record_from_event(
    *, event: ProposalWorkflowEventRecord, replayed: bool
) -> ProposalNarrativeReviewRecord:
    reason = event.reason_json
    return ProposalNarrativeReviewRecord(
        review_id=event.event_id,
        proposal_id=event.proposal_id,
        proposal_version_no=event.related_version_no or 0,
        narrative_id=str(reason.get("narrative_id") or ""),
        action=cast(ProposalNarrativeReviewAction, reason.get("review_action")),
        review_state=cast(ProposalNarrativeReviewedState, reason.get("review_state")),
        client_ready_status=cast(
            ProposalNarrativeClientReadyStatus, reason.get("client_ready_status")
        ),
        reviewed_by=event.actor_id,
        reviewed_at=event.occurred_at.isoformat(),
        reason=str(reason.get("reason") or ""),
        source_narrative_hash=str(reason.get("source_narrative_hash") or ""),
        replacement_narrative_id=(
            str(reason["replacement_narrative_id"])
            if reason.get("replacement_narrative_id") is not None
            else None
        ),
        replayed=replayed,
    )


def _review_state(action: ProposalNarrativeReviewAction) -> ProposalNarrativeReviewedState:
    if action == "APPROVE":
        return "APPROVED_FOR_ADVISOR_USE"
    if action == "REQUEST_REGENERATION":
        return "REGENERATION_REQUESTED"
    return "REJECTED"


def _client_ready_status(
    *,
    payload: ProposalNarrativeReviewRequest,
    narrative: dict[str, Any],
) -> ProposalNarrativeClientReadyStatus:
    if not payload.client_ready_release_requested:
        return "NOT_REQUESTED"
    if payload.action != "APPROVE":
        return "BLOCKED_REVIEW_REQUIRED"
    if narrative.get("status") != "READY_FOR_ADVISOR_REVIEW":
        return "BLOCKED_POLICY_OR_GUARDRAIL"
    if narrative.get("review_state") != "DRAFT":
        return "BLOCKED_POLICY_OR_GUARDRAIL"
    policy = narrative.get("narrative_policy")
    if isinstance(policy, dict) and policy.get("client_ready_blockers"):
        return "BLOCKED_POLICY_OR_GUARDRAIL"
    if any(
        isinstance(item, dict) and item.get("status") == "FAIL"
        for item in narrative.get("guardrail_results", [])
    ):
        return "BLOCKED_POLICY_OR_GUARDRAIL"
    return "APPROVED_FOR_CLIENT_READY"


def _require_reviewable_narrative(version: ProposalVersionRecord) -> None:
    narrative = _narrative(version)
    if not narrative.get("narrative_id"):
        raise ProposalNarrativeReviewError("PROPOSAL_NARRATIVE_NOT_FOUND")


def _narrative_id(version: ProposalVersionRecord) -> str:
    narrative_id = _narrative(version).get("narrative_id")
    return str(narrative_id) if narrative_id is not None else ""


def _narrative(version: ProposalVersionRecord) -> dict[str, Any]:
    narrative = version.artifact_json.get("proposal_narrative")
    if isinstance(narrative, dict):
        return deepcopy(narrative)
    raise ProposalNarrativeReviewError("PROPOSAL_NARRATIVE_NOT_FOUND")
