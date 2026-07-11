from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from src.core.policy_packs.persistence_models import PolicyEvaluationEventType
from src.core.proposals.exceptions import ProposalValidationError

PolicyEvaluationEventCommand = Literal[
    "policy_evaluation.sign_off_decision",
    "policy_evaluation.report_package",
    "policy_evaluation.ai_evidence",
]


@dataclass(frozen=True)
class PolicyEvaluationEventAuthority:
    event_type: PolicyEvaluationEventType
    command: PolicyEvaluationEventCommand
    contract_field: str
    required_reason_fields: frozenset[str]


POLICY_SIGN_OFF_EVENT_AUTHORITY = PolicyEvaluationEventAuthority(
    event_type="POLICY_EVALUATION_SIGN_OFF_RECORDED",
    command="policy_evaluation.sign_off_decision",
    contract_field="workflow_contract_version",
    required_reason_fields=frozenset(
        {
            "workflow_contract_version",
            "decision",
            "source_evaluation_hash",
            "client_ready_publication",
        }
    ),
)

POLICY_REPORT_PACKAGE_EVENT_AUTHORITY = PolicyEvaluationEventAuthority(
    event_type="POLICY_EVALUATION_REPORT_ARCHIVE_RECORDED",
    command="policy_evaluation.report_package",
    contract_field="policy_report_package_contract_version",
    required_reason_fields=frozenset(
        {
            "policy_report_package_contract_version",
            "policy_report_package_request_hash",
            "report_package_status",
            "source_evaluation_hash",
            "report_request_id",
            "policy_sign_off_package",
            "client_ready_publication",
        }
    ),
)

POLICY_AI_EVIDENCE_EVENT_AUTHORITY = PolicyEvaluationEventAuthority(
    event_type="POLICY_EVALUATION_AI_EVIDENCE_RECORDED",
    command="policy_evaluation.ai_evidence",
    contract_field="policy_ai_contract_version",
    required_reason_fields=frozenset(
        {
            "policy_ai_contract_version",
            "policy_ai_request_hash",
            "ai_status",
            "source_evaluation_hash",
            "requested_actions",
            "human_review_required",
            "authoritative_for_policy_status",
            "client_ready_publication",
            "lineage",
        }
    ),
)

_PRIVILEGED_EVENT_TYPES = frozenset(
    {
        "POLICY_EVALUATION_FINALIZED",
        "POLICY_EVALUATION_SIGN_OFF_RECORDED",
        "POLICY_EVALUATION_REPORT_ARCHIVE_RECORDED",
        "POLICY_EVALUATION_AI_EVIDENCE_RECORDED",
    }
)


def validate_policy_evaluation_event_authority(
    *,
    event_type: PolicyEvaluationEventType,
    reason: dict[str, Any],
    evaluation_hash: str,
    authority: PolicyEvaluationEventAuthority | None,
) -> None:
    if event_type == "POLICY_EVALUATION_REVIEW_RECORDED":
        return
    if event_type not in _PRIVILEGED_EVENT_TYPES:
        raise ProposalValidationError("POLICY_EVALUATION_EVENT_TYPE_UNSUPPORTED")
    if event_type == "POLICY_EVALUATION_FINALIZED":
        raise ProposalValidationError("POLICY_EVALUATION_FINALIZED_EVENT_REQUIRES_FINALIZE_COMMAND")
    if authority is None or authority.event_type != event_type:
        raise ProposalValidationError("POLICY_EVALUATION_PRIVILEGED_EVENT_REQUIRES_COMMAND")
    _validate_authority_reason(reason=reason, evaluation_hash=evaluation_hash, authority=authority)


def _validate_authority_reason(
    *,
    reason: dict[str, Any],
    evaluation_hash: str,
    authority: PolicyEvaluationEventAuthority,
) -> None:
    missing = sorted(field for field in authority.required_reason_fields if field not in reason)
    if missing:
        raise ProposalValidationError("POLICY_EVALUATION_PRIVILEGED_EVENT_REASON_INCOMPLETE")
    if reason.get("source_evaluation_hash") != evaluation_hash:
        raise ProposalValidationError("POLICY_EVALUATION_PRIVILEGED_EVENT_HASH_MISMATCH")
    if authority.contract_field not in reason:
        raise ProposalValidationError("POLICY_EVALUATION_PRIVILEGED_EVENT_CONTRACT_MISSING")


__all__ = [
    "POLICY_AI_EVIDENCE_EVENT_AUTHORITY",
    "POLICY_REPORT_PACKAGE_EVENT_AUTHORITY",
    "POLICY_SIGN_OFF_EVENT_AUTHORITY",
    "PolicyEvaluationEventAuthority",
    "validate_policy_evaluation_event_authority",
]
