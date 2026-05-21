from collections.abc import Collection
from copy import deepcopy
from datetime import datetime
from typing import Any

from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.models import ProposalResult
from src.core.proposals.lifecycle_events import build_new_version_created_event
from src.core.proposals.models import (
    ProposalRecord,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)


class ProposalVersionEligibilityError(Exception):
    pass


class ProposalVersionTerminalStateError(ProposalVersionEligibilityError):
    pass


class ProposalVersionConflictError(ProposalVersionEligibilityError):
    pass


class ProposalVersionPortfolioContextError(ProposalVersionEligibilityError):
    pass


def validate_create_version_state(
    *,
    proposal: ProposalRecord,
    expected_current_version_no: int | None,
    terminal_states: Collection[str],
) -> None:
    if proposal.current_state in terminal_states:
        raise ProposalVersionTerminalStateError("PROPOSAL_TERMINAL_STATE: cannot create version")
    if (
        expected_current_version_no is not None
        and expected_current_version_no != proposal.current_version_no
    ):
        raise ProposalVersionConflictError("VERSION_CONFLICT: expected_current_version_no mismatch")


def validate_create_version_portfolio_context(
    *,
    proposal_portfolio_id: str,
    request_portfolio_id: str,
    allow_portfolio_id_change: bool,
) -> None:
    if allow_portfolio_id_change:
        return
    if request_portfolio_id != proposal_portfolio_id:
        raise ProposalVersionPortfolioContextError("PORTFOLIO_CONTEXT_MISMATCH")


def build_proposal_version_record(
    *,
    proposal_version_id: str,
    proposal_id: str,
    version_no: int,
    request_hash: str,
    proposal_result: ProposalResult,
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    created_at: datetime,
    store_evidence_bundle: bool,
) -> ProposalVersionRecord:
    simulation_payload = proposal_result.model_dump(mode="json", warnings=False)
    simulation_hash_payload = strip_keys(
        simulation_payload,
        exclude={"correlation_id", "idempotency_key"},
    )
    simulation_hash = hash_canonical_payload(simulation_hash_payload)
    artifact_hash = artifact["evidence_bundle"]["hashes"]["artifact_hash"]
    return ProposalVersionRecord(
        proposal_version_id=proposal_version_id,
        proposal_id=proposal_id,
        version_no=version_no,
        created_at=created_at,
        request_hash=request_hash,
        artifact_hash=artifact_hash,
        simulation_hash=simulation_hash,
        status_at_creation=proposal_result.status,
        proposal_result_json=simulation_payload,
        artifact_json=deepcopy(artifact),
        evidence_bundle_json=deepcopy(evidence_bundle) if store_evidence_bundle else {},
        gate_decision_json=(
            proposal_result.gate_decision.model_dump(mode="json")
            if proposal_result.gate_decision is not None
            else None
        ),
    )


def apply_new_version_lifecycle_state(
    *,
    proposal: ProposalRecord,
    version_no: int,
    occurred_at: datetime,
) -> None:
    proposal.current_version_no = version_no
    proposal.current_state = "DRAFT"
    proposal.last_event_at = occurred_at


def build_new_version_created_event_and_apply_state(
    *,
    event_id: str,
    proposal: ProposalRecord,
    actor_id: str,
    occurred_at: datetime,
    related_version_no: int,
    correlation_id: str | None,
) -> ProposalWorkflowEventRecord:
    event = build_new_version_created_event(
        event_id=event_id,
        proposal=proposal,
        actor_id=actor_id,
        occurred_at=occurred_at,
        related_version_no=related_version_no,
        correlation_id=correlation_id,
    )
    apply_new_version_lifecycle_state(
        proposal=proposal,
        version_no=related_version_no,
        occurred_at=occurred_at,
    )
    return event
