import pytest

from src.core.proposals.workflow_rules import (
    ProposalWorkflowRuleError,
    execution_state_correlation,
    execution_status_for_event,
    resolve_approval_transition,
    resolve_execution_update_event,
    resolve_transition_state,
)


@pytest.mark.parametrize(
    ("current_state", "approval_type", "approved_event_type", "approved_next_state"),
    [
        ("RISK_REVIEW", "RISK", "RISK_APPROVED", "AWAITING_CLIENT_CONSENT"),
        ("COMPLIANCE_REVIEW", "COMPLIANCE", "COMPLIANCE_APPROVED", "AWAITING_CLIENT_CONSENT"),
        (
            "AWAITING_CLIENT_CONSENT",
            "CLIENT_CONSENT",
            "CLIENT_CONSENT_RECORDED",
            "EXECUTION_READY",
        ),
    ],
)
def test_resolve_approval_transition_maps_all_approval_types(
    current_state,
    approval_type,
    approved_event_type,
    approved_next_state,
):
    assert resolve_approval_transition(
        current_state=current_state,
        approval_type=approval_type,
        approved=True,
    ) == (approved_event_type, approved_next_state)
    assert resolve_approval_transition(
        current_state=current_state,
        approval_type=approval_type,
        approved=False,
    ) == ("REJECTED", "REJECTED")


def test_resolve_transition_state_allows_cancel_from_active_states():
    assert resolve_transition_state(current_state="DRAFT", event_type="CANCELLED") == "CANCELLED"


def test_resolve_transition_state_rejects_invalid_transition():
    with pytest.raises(ProposalWorkflowRuleError) as exc_info:
        resolve_transition_state(current_state="DRAFT", event_type="CLIENT_CONSENT_RECORDED")

    assert str(exc_info.value) == "INVALID_TRANSITION"


def test_resolve_approval_transition_maps_approved_and_rejected_paths():
    assert resolve_approval_transition(
        current_state="RISK_REVIEW",
        approval_type="RISK",
        approved=True,
    ) == ("RISK_APPROVED", "AWAITING_CLIENT_CONSENT")
    assert resolve_approval_transition(
        current_state="AWAITING_CLIENT_CONSENT",
        approval_type="CLIENT_CONSENT",
        approved=False,
    ) == ("REJECTED", "REJECTED")


def test_resolve_approval_transition_rejects_wrong_state_and_unknown_type():
    with pytest.raises(ProposalWorkflowRuleError) as state_exc:
        resolve_approval_transition(
            current_state="DRAFT",
            approval_type="CLIENT_CONSENT",
            approved=True,
        )
    with pytest.raises(ProposalWorkflowRuleError) as type_exc:
        resolve_approval_transition(
            current_state="DRAFT",
            approval_type="UNKNOWN",
            approved=True,
        )

    assert str(state_exc.value) == "INVALID_APPROVAL_STATE"
    assert str(type_exc.value) == "INVALID_APPROVAL_TYPE"


def test_execution_update_and_status_mappings_are_bounded():
    assert resolve_execution_update_event("PARTIALLY_EXECUTED") == (
        "EXECUTION_PARTIALLY_EXECUTED",
        "EXECUTION_READY",
    )
    assert execution_status_for_event("EXECUTION_PARTIALLY_EXECUTED") == "PARTIALLY_EXECUTED"
    assert execution_status_for_event("UNKNOWN") == "NOT_REQUESTED"
    assert (
        execution_state_correlation(handoff_status="PARTIALLY_EXECUTED")
        == "EXECUTION_REQUESTED_AND_PARTIAL_EXECUTION_EVENTS"
    )
    assert execution_state_correlation(handoff_status="UNKNOWN") == "NO_EXECUTION_EVENTS_RECORDED"
