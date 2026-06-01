from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.common.canonical import hash_canonical_payload
from src.core.common.idempotency import normalize_optional_idempotency_key
from src.core.policy_packs.models import (
    PolicyEvaluationAiEvidenceRequest,
    PolicyEvaluationAiEvidenceResponse,
)
from src.core.policy_packs.persistence import (
    append_policy_evaluation_event,
    get_policy_evaluation_record,
    list_policy_evaluation_events,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationAuditEvent,
    PolicyEvaluationRecord,
)
from src.core.policy_packs.workflow import get_policy_evaluation_workflow
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalValidationError,
)
from src.integrations.lotus_ai import (
    LotusAIPolicyEvidenceUnavailableError,
    build_policy_ai_unavailable_evidence,
    generate_policy_evidence_summary_with_lotus_ai,
)

_AI_CONTRACT_VERSION = "rfc0025.policy-ai-evidence-boundary.v1"
_CLIENT_READY_PUBLICATION = "BLOCKED"
_SUPPORTED_ACTIONS = {
    "SUMMARIZE_POLICY_POSTURE",
    "EXPLAIN_OPEN_REQUIREMENTS",
    "EXPLAIN_SIGN_OFF_EVIDENCE",
    "EXPLAIN_DISCLOSURE_AND_CONSENT_POSTURE",
    "EXPLAIN_SOURCE_GAPS",
}
_FORBIDDEN_ACTION_FRAGMENTS = (
    "APPROVE",
    "WAIVE",
    "MUTATE",
    "UPDATE",
    "RELEASE",
    "CLIENT_READY",
    "CLIENT-READY",
    "PUBLISH",
    "CERTIFY",
)


def request_policy_evaluation_ai_evidence(
    *,
    evaluation_id: str,
    payload: PolicyEvaluationAiEvidenceRequest,
    idempotency_key: str | None = None,
) -> PolicyEvaluationAiEvidenceResponse:
    idempotency_key = normalize_optional_idempotency_key(idempotency_key)
    record = get_policy_evaluation_record(evaluation_id=evaluation_id)
    _validate_ai_request(record=record, payload=payload)
    requested_actions = _normalize_requested_actions(payload.requested_actions)
    request_hash = _request_hash(
        record=record,
        requested_actions=requested_actions,
        payload=payload,
    )
    if idempotency_key:
        replayed_event = _find_replayed_ai_event(
            evaluation_id=evaluation_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replayed_event is not None:
            return PolicyEvaluationAiEvidenceResponse(
                evaluation=get_policy_evaluation_record(evaluation_id=evaluation_id),
                ai_event=replayed_event,
                policy_evidence=_policy_evidence_from_event(replayed_event),
                replayed=True,
            )

    evidence_packet = _build_policy_ai_evidence_packet(
        record=record,
        requested_actions=requested_actions,
    )
    try:
        draft = generate_policy_evidence_summary_with_lotus_ai(
            policy_evidence=evidence_packet,
            requested_actions=requested_actions,
            requested_by=payload.requested_by,
            reason=payload.reason,
        )
        ai_status = "REVIEW_REQUIRED"
    except LotusAIPolicyEvidenceUnavailableError as exc:
        draft = build_policy_ai_unavailable_evidence(str(exc))
        ai_status = "UNAVAILABLE"

    reason = {
        "policy_ai_contract_version": _AI_CONTRACT_VERSION,
        "policy_ai_request_hash": request_hash,
        "ai_status": ai_status,
        "source_evaluation_hash": payload.source_evaluation_hash,
        "requested_actions": requested_actions,
        "client_ready_publication": _CLIENT_READY_PUBLICATION,
        "human_review_required": True,
        "authoritative_for_policy_status": False,
        "forbidden_actions": [
            "policy_status_mutation",
            "rule_result_mutation",
            "approval_or_waiver_creation",
            "disclosure_or_consent_mutation",
            "client_ready_publication",
        ],
        "redaction_profile": evidence_packet["redaction_profile"],
        "lineage": draft.lineage,
        "sections": list(draft.sections),
        "review_guidance": list(draft.review_guidance),
        "reason": deepcopy(payload.reason),
    }
    event = append_policy_evaluation_event(
        evaluation_id=evaluation_id,
        event_type="POLICY_EVALUATION_AI_EVIDENCE_RECORDED",
        actor_id=payload.requested_by,
        idempotency_key=idempotency_key,
        reason=reason,
    )
    return PolicyEvaluationAiEvidenceResponse(
        evaluation=get_policy_evaluation_record(evaluation_id=evaluation_id),
        ai_event=event,
        policy_evidence=_policy_evidence_from_event(event),
        replayed=False,
    )


def _validate_ai_request(
    *, record: PolicyEvaluationRecord, payload: PolicyEvaluationAiEvidenceRequest
) -> None:
    if payload.source_evaluation_hash != record.evaluation_hash:
        raise ProposalValidationError("POLICY_AI_EVIDENCE_HASH_MISMATCH")
    _normalize_requested_actions(payload.requested_actions)


def _normalize_requested_actions(actions: list[str]) -> list[str]:
    normalized = [str(action).strip().upper() for action in actions if str(action).strip()]
    if not normalized:
        raise ProposalValidationError("POLICY_AI_EVIDENCE_ACTION_REQUIRED")
    forbidden = [
        action
        for action in normalized
        if action not in _SUPPORTED_ACTIONS
        or any(fragment in action for fragment in _FORBIDDEN_ACTION_FRAGMENTS)
    ]
    if forbidden:
        raise ProposalValidationError("POLICY_AI_EVIDENCE_FORBIDDEN_ACTION")
    return normalized


def _find_replayed_ai_event(
    *, evaluation_id: str, idempotency_key: str, request_hash: str
) -> PolicyEvaluationAuditEvent | None:
    for event in list_policy_evaluation_events(evaluation_id=evaluation_id):
        if event.idempotency_key != idempotency_key:
            continue
        prior_hash = event.reason_json.get("policy_ai_request_hash")
        if prior_hash != request_hash:
            raise ProposalIdempotencyConflictError("POLICY_EVALUATION_IDEMPOTENCY_KEY_CONFLICT")
        return event
    return None


def _build_policy_ai_evidence_packet(
    *, record: PolicyEvaluationRecord, requested_actions: list[str]
) -> dict[str, Any]:
    workflow = get_policy_evaluation_workflow(evaluation_id=record.evaluation_id)
    events = list_policy_evaluation_events(evaluation_id=record.evaluation_id)
    return {
        "packet_type": "ADVISORY_POLICY_AI_EVIDENCE_PACKET",
        "packet_version": _AI_CONTRACT_VERSION,
        "evaluation_id": record.evaluation_id,
        "proposal_id": record.proposal_id,
        "proposal_version_id": record.proposal_version_id,
        "policy_pack_id": record.policy_pack_id,
        "policy_version": record.policy_version,
        "evaluation_status": record.evaluation_status,
        "evaluation_hash": record.evaluation_hash,
        "policy_content_hash": record.policy_content_hash,
        "source_evidence_hash": record.source_evidence_hash,
        "rule_results": [
            {
                "rule_id": item.get("rule_id"),
                "status": item.get("status"),
                "severity": item.get("severity"),
                "reason_codes": item.get("reason_codes", []),
                "source_refs": item.get("source_refs", []),
            }
            for item in _rule_results(record)
        ],
        "approval_dependencies": list(record.approval_dependencies),
        "disclosure_requirements": list(record.disclosure_requirements),
        "consent_requirements": list(record.consent_requirements),
        "source_refs": list(record.source_refs),
        "source_gaps": list(record.source_gaps),
        "workflow": workflow.model_dump(mode="json"),
        "event_summary": [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "actor_id": event.actor_id,
                "occurred_at": event.occurred_at,
                "reason_codes": event.reason_json.get("reason_codes", []),
            }
            for event in events
        ],
        "requested_actions": requested_actions,
        "redaction_profile": {
            "profile_id": "policy_ai_bounded_evidence_redaction.v1",
            "raw_source_evidence_included": False,
            "raw_client_identity_included": False,
            "free_text_notes_included": False,
            "full_position_payload_included": False,
            "allowed_content": [
                "policy_status",
                "rule_result_status",
                "reason_codes",
                "source_refs",
                "workflow_posture",
                "append_only_event_summary",
            ],
        },
        "client_ready_publication": _CLIENT_READY_PUBLICATION,
        "human_review_required": True,
        "authoritative_for_policy_status": False,
    }


def _rule_results(record: PolicyEvaluationRecord) -> list[dict[str, Any]]:
    rule_results = record.evaluation_json.get("rule_results")
    return rule_results if isinstance(rule_results, list) else []


def _policy_evidence_from_event(event: PolicyEvaluationAuditEvent) -> dict[str, Any]:
    reason = event.reason_json
    return {
        "status": reason.get("ai_status", "UNAVAILABLE"),
        "sections": reason.get("sections", []),
        "lineage": reason.get("lineage", {}),
        "review_guidance": reason.get("review_guidance", []),
        "client_ready_publication": _CLIENT_READY_PUBLICATION,
        "human_review_required": True,
        "authoritative_for_policy_status": False,
        "forbidden_actions": reason.get("forbidden_actions", []),
        "redaction_profile": reason.get("redaction_profile", {}),
    }


def _request_hash(
    *,
    record: PolicyEvaluationRecord,
    requested_actions: list[str],
    payload: PolicyEvaluationAiEvidenceRequest,
) -> str:
    return str(
        hash_canonical_payload(
            {
                "operation": "POLICY_AI_EVIDENCE_REQUESTED",
                "evaluation_id": record.evaluation_id,
                "source_evaluation_hash": payload.source_evaluation_hash,
                "requested_by": payload.requested_by,
                "requested_actions": requested_actions,
                "reason": payload.reason,
            }
        )
    )
