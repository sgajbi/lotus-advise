from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

from src.core.common.idempotency import normalize_optional_idempotency_key
from src.core.policy_packs.event_authority import POLICY_SIGN_OFF_EVENT_AUTHORITY
from src.core.policy_packs.persistence import (
    append_policy_evaluation_event,
    get_policy_evaluation_record,
    list_policy_evaluation_events,
)
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationEventType,
)
from src.core.policy_packs.supportability import (
    CLIENT_READY_PUBLICATION_POSTURE,
    POLICY_WORKFLOW_CONTRACT_VERSION,
    policy_sign_off_package_posture,
)
from src.core.policy_packs.workflow_decision import validate_policy_sign_off_decision
from src.core.policy_packs.workflow_models import (
    PolicyEvaluationSignOffDecisionRequest,
    PolicyEvaluationSignOffDecisionResponse,
    PolicyEvaluationWorkflowResponse,
)
from src.core.policy_packs.workflow_projection import build_policy_evaluation_workflow_projection
from src.core.proposals.exceptions import ProposalValidationError

_WORKFLOW_CONTRACT_VERSION = POLICY_WORKFLOW_CONTRACT_VERSION
_CLIENT_READY_PUBLICATION = CLIENT_READY_PUBLICATION_POSTURE


def get_policy_evaluation_workflow(
    *, evaluation_id: str, now: datetime | None = None
) -> PolicyEvaluationWorkflowResponse:
    record = get_policy_evaluation_record(evaluation_id=evaluation_id)
    events = list_policy_evaluation_events(evaluation_id=evaluation_id)
    return build_policy_evaluation_workflow_projection(
        record=record,
        events=events,
        now=now or datetime.now(UTC),
        client_ready_publication=_CLIENT_READY_PUBLICATION,
    )


def record_policy_evaluation_sign_off_decision(
    *,
    evaluation_id: str,
    payload: PolicyEvaluationSignOffDecisionRequest,
    idempotency_key: str | None = None,
    now: datetime | None = None,
) -> PolicyEvaluationSignOffDecisionResponse:
    idempotency_key = normalize_optional_idempotency_key(idempotency_key)
    decision_time = now or datetime.now(UTC)
    record = get_policy_evaluation_record(evaluation_id=evaluation_id)
    if payload.source_evaluation_hash != record.evaluation_hash:
        raise ProposalValidationError("POLICY_EVALUATION_SIGN_OFF_HASH_MISMATCH")

    existing_events = list_policy_evaluation_events(evaluation_id=evaluation_id)
    before = build_policy_evaluation_workflow_projection(
        record=record,
        events=existing_events,
        now=decision_time,
        client_ready_publication=_CLIENT_READY_PUBLICATION,
    )
    validate_policy_sign_off_decision(record=record, workflow=before, payload=payload)

    event_type: PolicyEvaluationEventType = (
        "POLICY_EVALUATION_SIGN_OFF_RECORDED"
        if payload.decision == "APPROVE_FOR_POLICY_SIGN_OFF"
        else "POLICY_EVALUATION_REVIEW_RECORDED"
    )
    event = append_policy_evaluation_event(
        evaluation_id=evaluation_id,
        event_type=event_type,
        actor_id=payload.actor_id,
        idempotency_key=idempotency_key,
        authority=POLICY_SIGN_OFF_EVENT_AUTHORITY
        if event_type == "POLICY_EVALUATION_SIGN_OFF_RECORDED"
        else None,
        reason={
            "workflow_contract_version": _WORKFLOW_CONTRACT_VERSION,
            "decision": payload.decision,
            "source_evaluation_hash": payload.source_evaluation_hash,
            "resolved_approval_dependencies": list(payload.resolved_approval_dependencies),
            "satisfied_disclosure_requirements": list(payload.satisfied_disclosure_requirements),
            "satisfied_consent_requirements": list(payload.satisfied_consent_requirements),
            "conflict_review_outcome": payload.conflict_review_outcome,
            "client_ready_publication": _CLIENT_READY_PUBLICATION,
            "reason": deepcopy(payload.reason),
        },
    )
    workflow = build_policy_evaluation_workflow_projection(
        record=record,
        events=[*existing_events, event],
        now=decision_time,
        client_ready_publication=_CLIENT_READY_PUBLICATION,
    )
    return PolicyEvaluationSignOffDecisionResponse(
        workflow=workflow,
        sign_off_event=event,
        replay_metadata={
            "workflow_contract_version": _WORKFLOW_CONTRACT_VERSION,
            "evaluation_hash": record.evaluation_hash,
            "policy_pack_id": record.policy_pack_id,
            "policy_version": record.policy_version,
            "client_ready_publication": _CLIENT_READY_PUBLICATION,
            "report_render_archive_realization": policy_sign_off_package_posture()[
                "report_render_archive_realization"
            ],
        },
    )
