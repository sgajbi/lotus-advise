from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from src.core.policy_packs.models import (
    PolicyEvaluationAuditEvent,
    PolicyEvaluationEventType,
    PolicyEvaluationRequirementProjection,
    PolicyEvaluationSignOffDecisionRequest,
    PolicyEvaluationSignOffDecisionResponse,
    PolicyEvaluationWorkflowResponse,
)
from src.core.policy_packs.persistence import (
    append_policy_evaluation_event,
    get_policy_evaluation_record,
    list_policy_evaluation_events,
)
from src.core.proposals.exceptions import ProposalValidationError

_WORKFLOW_CONTRACT_VERSION = "rfc0025.policy-sign-off-workflow.v1"
_CLIENT_READY_PUBLICATION = "BLOCKED"


def get_policy_evaluation_workflow(
    *, evaluation_id: str, now: datetime | None = None
) -> PolicyEvaluationWorkflowResponse:
    record = get_policy_evaluation_record(evaluation_id=evaluation_id)
    events = list_policy_evaluation_events(evaluation_id=evaluation_id)
    return _build_workflow(record=record, events=events, now=now or datetime.now(UTC))


def record_policy_evaluation_sign_off_decision(
    *,
    evaluation_id: str,
    payload: PolicyEvaluationSignOffDecisionRequest,
    idempotency_key: str | None = None,
    now: datetime | None = None,
) -> PolicyEvaluationSignOffDecisionResponse:
    decision_time = now or datetime.now(UTC)
    record = get_policy_evaluation_record(evaluation_id=evaluation_id)
    if payload.source_evaluation_hash != record.evaluation_hash:
        raise ProposalValidationError("POLICY_EVALUATION_SIGN_OFF_HASH_MISMATCH")

    existing_events = list_policy_evaluation_events(evaluation_id=evaluation_id)
    before = _build_workflow(record=record, events=existing_events, now=decision_time)
    _validate_decision(record=record, workflow=before, payload=payload)

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
    workflow = _build_workflow(
        record=record,
        events=[*existing_events, event],
        now=decision_time,
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
            "report_render_archive_realization": "NOT_IMPLEMENTED",
        },
    )


def _validate_decision(
    *,
    record: Any,
    workflow: PolicyEvaluationWorkflowResponse,
    payload: PolicyEvaluationSignOffDecisionRequest,
) -> None:
    if payload.actor_id == record.created_by and payload.decision == "APPROVE_FOR_POLICY_SIGN_OFF":
        raise ProposalValidationError("POLICY_EVALUATION_SIGN_OFF_REQUIRES_MAKER_CHECKER")
    if payload.decision != "APPROVE_FOR_POLICY_SIGN_OFF":
        return

    blockers = _approval_blockers(record=record, payload=payload)
    if workflow.conflict_posture["status"] == "BLOCKED" and payload.conflict_review_outcome != (
        "NO_MATERIAL_CONFLICT_REMAINING"
    ):
        blockers.append("CONFLICT_REVIEW_OUTCOME_REQUIRED")
    if record.evaluation_status == "BLOCKED":
        blockers.append("BLOCKED_POLICY_EVALUATION_CANNOT_BE_SIGNED_OFF")
    if blockers:
        raise ProposalValidationError("POLICY_EVALUATION_SIGN_OFF_REQUIREMENTS_OPEN")


def _approval_blockers(
    *, record: Any, payload: PolicyEvaluationSignOffDecisionRequest
) -> list[str]:
    blockers: list[str] = []
    resolved = set(payload.resolved_approval_dependencies)
    disclosures = set(payload.satisfied_disclosure_requirements)
    consents = set(payload.satisfied_consent_requirements)
    missing_approvals = sorted(set(record.approval_dependencies) - resolved)
    missing_disclosures = sorted(set(record.disclosure_requirements) - disclosures)
    missing_consents = sorted(set(record.consent_requirements) - consents)
    if missing_approvals:
        blockers.extend(f"APPROVAL_DEPENDENCY_OPEN:{item}" for item in missing_approvals)
    if missing_disclosures:
        blockers.extend(f"DISCLOSURE_REQUIREMENT_OPEN:{item}" for item in missing_disclosures)
    if missing_consents:
        blockers.extend(f"CONSENT_REQUIREMENT_OPEN:{item}" for item in missing_consents)
    return blockers


def _build_workflow(
    *, record: Any, events: list[PolicyEvaluationAuditEvent], now: datetime
) -> PolicyEvaluationWorkflowResponse:
    sign_off_events = [
        event for event in events if event.event_type == "POLICY_EVALUATION_SIGN_OFF_RECORDED"
    ]
    latest_sign_off = sign_off_events[-1] if sign_off_events else None
    resolved = _approved_sign_off_values(events, "resolved_approval_dependencies")
    disclosures = _approved_sign_off_values(events, "satisfied_disclosure_requirements")
    consents = _approved_sign_off_values(events, "satisfied_consent_requirements")
    conflict_posture = _conflict_posture(record=record, events=events)
    approval_dependencies = [
        _requirement(
            requirement_id=item,
            requirement_type="approval",
            owner_role=_owner_role(item),
            generated_at=record.generated_at,
            now=now,
            satisfied=item in resolved,
        )
        for item in record.approval_dependencies
    ]
    disclosure_requirements = [
        _requirement(
            requirement_id=item,
            requirement_type="disclosure",
            owner_role="INVESTMENT_COUNSELLOR",
            generated_at=record.generated_at,
            now=now,
            satisfied=item in disclosures,
        )
        for item in record.disclosure_requirements
    ]
    consent_requirements = [
        _requirement(
            requirement_id=item,
            requirement_type="consent",
            owner_role="ADVISOR",
            generated_at=record.generated_at,
            now=now,
            satisfied=item in consents,
        )
        for item in record.consent_requirements
    ]
    all_requirements = [
        *approval_dependencies,
        *disclosure_requirements,
        *consent_requirements,
    ]
    blockers = _workflow_blockers(
        record=record,
        requirements=all_requirements,
        conflict_posture=conflict_posture,
    )
    return PolicyEvaluationWorkflowResponse(
        evaluation_id=record.evaluation_id,
        proposal_id=record.proposal_id,
        proposal_version_id=record.proposal_version_id,
        evaluation_status=record.evaluation_status,
        approval_dependencies=approval_dependencies,
        disclosure_requirements=disclosure_requirements,
        consent_requirements=consent_requirements,
        conflict_posture=conflict_posture,
        sla_posture=_sla_posture(requirements=all_requirements, now=now),
        sign_off_status=_sign_off_status(
            blockers=blockers,
            latest_sign_off=latest_sign_off,
            evaluation_status=record.evaluation_status,
        ),
        sign_off_blockers=blockers,
        maker_checker_required=True,
        latest_sign_off_event=latest_sign_off,
        client_ready_publication=_CLIENT_READY_PUBLICATION,
    )


def _approved_sign_off_values(events: list[PolicyEvaluationAuditEvent], key: str) -> set[str]:
    values: set[str] = set()
    for event in events:
        if event.event_type != "POLICY_EVALUATION_SIGN_OFF_RECORDED":
            continue
        if event.reason_json.get("decision") != "APPROVE_FOR_POLICY_SIGN_OFF":
            continue
        raw = event.reason_json.get(key, [])
        if isinstance(raw, list):
            values.update(str(item) for item in raw)
    return values


def _conflict_posture(*, record: Any, events: list[PolicyEvaluationAuditEvent]) -> dict[str, Any]:
    conflict_results = [
        result
        for result in record.evaluation_json.get("rule_results", [])
        if isinstance(result, dict) and "CONFLICT" in str(result.get("rule_id", ""))
    ]
    reason_codes: list[str] = []
    blockers: list[str] = []
    for result in conflict_results:
        reason_codes.extend(str(item) for item in result.get("reason_codes", []))
        blockers.extend(str(item) for item in result.get("required_actions", []))
    outcomes = [
        str(event.reason_json.get("conflict_review_outcome"))
        for event in events
        if event.reason_json.get("conflict_review_outcome")
    ]
    if "NO_MATERIAL_CONFLICT_REMAINING" in outcomes:
        return {
            "status": "SATISFIED",
            "reason_codes": _unique(reason_codes),
            "blockers": [],
            "review_outcome": "NO_MATERIAL_CONFLICT_REMAINING",
        }
    blocked = any("MATERIAL_CONFLICT" in code for code in reason_codes) or any(
        blocker in {"SUPERVISORY_CONFLICT_REVIEW", "REVIEW_CONFLICT_OF_INTEREST"}
        for blocker in blockers
    )
    return {
        "status": "BLOCKED" if blocked else "SATISFIED",
        "reason_codes": _unique(reason_codes),
        "blockers": _unique(blockers) if blocked else [],
        "review_outcome": outcomes[-1] if outcomes else None,
    }


def _requirement(
    *,
    requirement_id: str,
    requirement_type: str,
    owner_role: str,
    generated_at: str,
    now: datetime,
    satisfied: bool,
) -> PolicyEvaluationRequirementProjection:
    review_sla = _review_sla(requirement_id=requirement_id, owner_role=owner_role)
    due_at = _due_at(generated_at=generated_at, review_sla=review_sla)
    overdue = bool(due_at and _parse_datetime(due_at) < now)
    return PolicyEvaluationRequirementProjection(
        requirement_id=requirement_id,
        requirement_type=requirement_type,
        status="SATISFIED" if satisfied else "OPEN",
        owner_role=owner_role,
        review_sla=review_sla,
        due_at=due_at,
        reason_codes=["POLICY_REQUIREMENT_SATISFIED"]
        if satisfied
        else ["POLICY_REQUIREMENT_OVERDUE" if overdue else "POLICY_REQUIREMENT_OPEN"],
    )


def _workflow_blockers(
    *,
    record: Any,
    requirements: list[PolicyEvaluationRequirementProjection],
    conflict_posture: dict[str, Any],
) -> list[str]:
    blockers = [
        f"{requirement.requirement_type.upper()}_REQUIREMENT_OPEN:{requirement.requirement_id}"
        for requirement in requirements
        if requirement.status != "SATISFIED"
    ]
    if conflict_posture["status"] == "BLOCKED":
        blockers.extend(str(item) for item in conflict_posture["blockers"])
    if record.evaluation_status == "BLOCKED":
        blockers.append("BLOCKED_POLICY_EVALUATION_CANNOT_BE_SIGNED_OFF")
    return _unique(blockers)


def _sign_off_status(
    *,
    blockers: list[str],
    latest_sign_off: PolicyEvaluationAuditEvent | None,
    evaluation_status: str,
) -> str:
    if latest_sign_off is not None and latest_sign_off.reason_json.get("decision") == (
        "APPROVE_FOR_POLICY_SIGN_OFF"
    ):
        return "SIGNED_OFF"
    if evaluation_status == "BLOCKED" or any("CONFLICT" in blocker for blocker in blockers):
        return "BLOCKED"
    if blockers:
        return "PENDING_REVIEW"
    return "READY_FOR_SIGN_OFF"


def _sla_posture(
    *, requirements: list[PolicyEvaluationRequirementProjection], now: datetime
) -> dict[str, Any]:
    open_requirements = [item for item in requirements if item.status != "SATISFIED"]
    overdue = [
        item.requirement_id
        for item in open_requirements
        if item.due_at is not None and _parse_datetime(item.due_at) < now
    ]
    return {
        "status": "OVERDUE" if overdue else "WITHIN_SLA",
        "open_requirement_count": len(open_requirements),
        "overdue_requirement_ids": overdue,
        "as_of": now.isoformat(),
    }


def _owner_role(requirement_id: str) -> str:
    if requirement_id.startswith("SUPERVISORY_"):
        return "SUPERVISOR"
    if requirement_id.startswith("POLICY_STEWARD_"):
        return "POLICY_STEWARD"
    if "DISCLOSURE" in requirement_id:
        return "INVESTMENT_COUNSELLOR"
    if "CONFLICT" in requirement_id:
        return "SUPERVISOR"
    return "ADVISOR"


def _review_sla(*, requirement_id: str, owner_role: str) -> str:
    if owner_role == "SUPERVISOR" or "CONFLICT" in requirement_id:
        return "P2D"
    return "P1D"


def _due_at(*, generated_at: str, review_sla: str) -> str | None:
    generated = _parse_datetime(generated_at)
    if review_sla == "P2D":
        return (generated + timedelta(days=2)).isoformat()
    if review_sla == "P1D":
        return (generated + timedelta(days=1)).isoformat()
    return None


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
