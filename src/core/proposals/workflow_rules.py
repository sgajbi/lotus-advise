from src.core.proposals.models import ProposalWorkflowState

TERMINAL_STATES = {"EXECUTED", "REJECTED", "CANCELLED", "EXPIRED"}

TRANSITION_MAP: dict[tuple[ProposalWorkflowState, str], ProposalWorkflowState] = {
    ("DRAFT", "SUBMITTED_FOR_RISK_REVIEW"): "RISK_REVIEW",
    ("DRAFT", "SUBMITTED_FOR_COMPLIANCE_REVIEW"): "COMPLIANCE_REVIEW",
    ("RISK_REVIEW", "RISK_APPROVED"): "AWAITING_CLIENT_CONSENT",
    ("RISK_REVIEW", "REJECTED"): "REJECTED",
    ("COMPLIANCE_REVIEW", "COMPLIANCE_APPROVED"): "AWAITING_CLIENT_CONSENT",
    ("COMPLIANCE_REVIEW", "REJECTED"): "REJECTED",
    ("AWAITING_CLIENT_CONSENT", "CLIENT_CONSENT_RECORDED"): "EXECUTION_READY",
    ("AWAITING_CLIENT_CONSENT", "REJECTED"): "REJECTED",
    ("EXECUTION_READY", "EXECUTION_REQUESTED"): "EXECUTION_READY",
    ("EXECUTION_READY", "EXECUTED"): "EXECUTED",
    ("EXECUTION_READY", "EXPIRED"): "EXPIRED",
}

EXECUTION_STATUS_EVENT_TYPES = {
    "EXECUTION_REQUESTED",
    "EXECUTION_ACCEPTED",
    "EXECUTION_PARTIALLY_EXECUTED",
    "EXECUTION_REJECTED",
    "EXECUTION_CANCELLED",
    "EXECUTION_EXPIRED",
    "EXECUTED",
}

EXECUTION_UPDATE_EVENT_MAP: dict[str, tuple[str, ProposalWorkflowState]] = {
    "ACCEPTED": ("EXECUTION_ACCEPTED", "EXECUTION_READY"),
    "PARTIALLY_EXECUTED": ("EXECUTION_PARTIALLY_EXECUTED", "EXECUTION_READY"),
    "REJECTED": ("EXECUTION_REJECTED", "REJECTED"),
    "CANCELLED": ("EXECUTION_CANCELLED", "CANCELLED"),
    "EXPIRED": ("EXECUTION_EXPIRED", "EXPIRED"),
    "EXECUTED": ("EXECUTED", "EXECUTED"),
}

EXECUTION_STATUS_BY_EVENT_TYPE = {
    "EXECUTION_REQUESTED": "REQUESTED",
    "EXECUTION_ACCEPTED": "ACCEPTED",
    "EXECUTION_PARTIALLY_EXECUTED": "PARTIALLY_EXECUTED",
    "EXECUTION_REJECTED": "REJECTED",
    "EXECUTION_CANCELLED": "CANCELLED",
    "EXECUTION_EXPIRED": "EXPIRED",
    "EXECUTED": "EXECUTED",
}

EXECUTION_STATE_CORRELATION_BY_STATUS = {
    "REQUESTED": "EXECUTION_REQUESTED_EVENT",
    "ACCEPTED": "EXECUTION_REQUESTED_AND_ACCEPTED_EVENTS",
    "PARTIALLY_EXECUTED": "EXECUTION_REQUESTED_AND_PARTIAL_EXECUTION_EVENTS",
    "EXECUTED": "EXECUTION_REQUESTED_AND_EXECUTED_EVENTS",
    "REJECTED": "EXECUTION_REQUESTED_AND_REJECTED_EVENTS",
    "CANCELLED": "EXECUTION_REQUESTED_AND_CANCELLED_EVENTS",
    "EXPIRED": "EXECUTION_REQUESTED_AND_EXPIRED_EVENTS",
}

APPROVAL_TRANSITION_RULES: dict[
    str,
    tuple[ProposalWorkflowState, str, ProposalWorkflowState],
] = {
    "RISK": ("RISK_REVIEW", "RISK_APPROVED", "AWAITING_CLIENT_CONSENT"),
    "COMPLIANCE": ("COMPLIANCE_REVIEW", "COMPLIANCE_APPROVED", "AWAITING_CLIENT_CONSENT"),
    "CLIENT_CONSENT": (
        "AWAITING_CLIENT_CONSENT",
        "CLIENT_CONSENT_RECORDED",
        "EXECUTION_READY",
    ),
}


class ProposalWorkflowRuleError(ValueError):
    pass


def resolve_transition_state(
    *,
    current_state: ProposalWorkflowState,
    event_type: str,
) -> ProposalWorkflowState:
    if event_type == "CANCELLED" and current_state not in TERMINAL_STATES:
        return "CANCELLED"
    next_state = TRANSITION_MAP.get((current_state, event_type))
    if next_state is None:
        raise ProposalWorkflowRuleError("INVALID_TRANSITION")
    return next_state


def resolve_approval_transition(
    *,
    current_state: ProposalWorkflowState,
    approval_type: str,
    approved: bool,
) -> tuple[str, ProposalWorkflowState]:
    rule = APPROVAL_TRANSITION_RULES.get(approval_type)
    if rule is None:
        raise ProposalWorkflowRuleError("INVALID_APPROVAL_TYPE")

    required_state, approved_event_type, approved_next_state = rule
    if current_state != required_state:
        raise ProposalWorkflowRuleError("INVALID_APPROVAL_STATE")
    if not approved:
        return "REJECTED", "REJECTED"
    return approved_event_type, approved_next_state


def resolve_execution_update_event(update_status: str) -> tuple[str, ProposalWorkflowState]:
    return EXECUTION_UPDATE_EVENT_MAP[update_status]


def execution_status_for_event(event_type: str) -> str:
    return EXECUTION_STATUS_BY_EVENT_TYPE.get(event_type, "NOT_REQUESTED")


def execution_state_correlation(*, handoff_status: str) -> str:
    return EXECUTION_STATE_CORRELATION_BY_STATUS.get(handoff_status, "NO_EXECUTION_EVENTS_RECORDED")
