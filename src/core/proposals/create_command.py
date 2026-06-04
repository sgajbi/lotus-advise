from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from src.core.proposals.command_validation import validate_proposal_simulation_flag
from src.core.proposals.context_evidence import build_context_resolution_evidence
from src.core.proposals.context_hashing import build_create_request_hash
from src.core.proposals.context_resolution import (
    ProposalContextResolutionError,
    resolve_create_request,
)
from src.core.proposals.create_persistence import persist_created_proposal
from src.core.proposals.error_details import (
    PROPOSAL_CONTEXT_RESOLUTION_FAILED_DETAIL,
    safe_proposal_error_detail,
)
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalValidationError,
)
from src.core.proposals.idempotency_read_model import load_proposal_idempotency_read_model
from src.core.proposals.idempotency_validation import require_proposal_idempotency_key
from src.core.proposals.identifiers import (
    new_proposal_id,
    new_proposal_version_id,
    new_workflow_event_id,
)
from src.core.proposals.lifecycle import (
    ProposalLifecycleOriginError,
    validate_lifecycle_origin,
)
from src.core.proposals.materialization import build_proposal_version_materialization
from src.core.proposals.models import (
    ProposalCreateRequest,
    ProposalCreateResponse,
    ProposalLifecycleOrigin,
)
from src.core.proposals.projections import to_create_response
from src.core.proposals.records import build_proposal_create_command_state
from src.core.proposals.replay_views import build_create_response_from_replay_referents
from src.core.proposals.repository import ProposalRepository
from src.core.proposals.simulation_execution import run_advisory_proposal_simulation
from src.core.proposals.versions import build_proposal_version_record


def create_proposal_command(
    *,
    repository: ProposalRepository,
    payload: ProposalCreateRequest,
    idempotency_key: str,
    correlation_id: str | None,
    lifecycle_origin: ProposalLifecycleOrigin,
    source_workspace_id: str | None,
    replay_lineage: dict[str, Any] | None,
    context_resolution_override: dict[str, Any] | None,
    store_evidence_bundle: bool,
    require_proposal_simulation_flag: bool,
    utc_now: Callable[[], datetime],
) -> ProposalCreateResponse:
    idempotency_key = require_proposal_idempotency_key(idempotency_key)
    try:
        validate_lifecycle_origin(
            lifecycle_origin=lifecycle_origin,
            source_workspace_id=source_workspace_id,
        )
    except ProposalLifecycleOriginError as exc:
        raise ProposalValidationError(str(exc)) from exc

    now = utc_now()
    try:
        resolved_request = resolve_create_request(payload)
    except ProposalContextResolutionError as exc:
        raise ProposalValidationError(
            safe_proposal_error_detail(
                str(exc),
                fallback=PROPOSAL_CONTEXT_RESOLUTION_FAILED_DETAIL,
            )
        ) from exc
    request_hash = build_create_request_hash(payload=payload, resolved=resolved_request)

    idempotency_read_model = load_proposal_idempotency_read_model(
        repository=repository,
        idempotency_key=idempotency_key,
    )
    existing = idempotency_read_model.record
    if existing is not None:
        if existing.request_hash != request_hash:
            raise ProposalIdempotencyConflictError(
                "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"
            )
        return build_create_response_from_replay_referents(
            repository=repository,
            proposal_id=existing.proposal_id,
            version_no=existing.proposal_version_no,
        )

    validate_proposal_simulation_flag(
        request=resolved_request.simulate_request,
        require_simulation_flag=require_proposal_simulation_flag,
    )
    context_resolution = build_context_resolution_evidence(resolved_request)
    proposal_result = run_advisory_proposal_simulation(
        request=resolved_request.simulate_request,
        resolved_as_of=resolved_request.resolved_context.as_of,
        input_mode=resolved_request.input_mode,
        request_hash=request_hash,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        policy_context=context_resolution["advisory_policy_context"],
    )
    materialization = build_proposal_version_materialization(
        request=resolved_request.simulate_request,
        proposal_result=proposal_result,
        created_at=now,
        context_resolution=context_resolution,
        context_resolution_override=context_resolution_override,
        replay_lineage=replay_lineage,
    )

    proposal_id = new_proposal_id()
    version_no = 1
    command_state = build_proposal_create_command_state(
        proposal_id=proposal_id,
        portfolio_id=resolved_request.simulate_request.portfolio_snapshot.portfolio_id,
        mandate_id=resolved_request.metadata.mandate_id,
        jurisdiction=resolved_request.metadata.jurisdiction,
        created_by=payload.created_by,
        created_at=now,
        version_no=version_no,
        title=resolved_request.metadata.title,
        advisor_notes=resolved_request.metadata.advisor_notes,
        lifecycle_origin=lifecycle_origin,
        source_workspace_id=source_workspace_id,
        event_id=new_workflow_event_id(),
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    proposal = command_state.proposal
    version = build_proposal_version_record(
        proposal_version_id=new_proposal_version_id(),
        proposal_id=proposal_id,
        version_no=version_no,
        request_hash=request_hash,
        proposal_result=proposal_result,
        artifact=materialization.artifact.model_dump(mode="json"),
        evidence_bundle=materialization.evidence_bundle,
        created_at=now,
        store_evidence_bundle=store_evidence_bundle,
    )
    created_event = command_state.created_event

    persist_created_proposal(
        repository=repository,
        command_state=command_state,
        version=version,
    )

    return to_create_response(proposal=proposal, version=version, latest_event=created_event)


__all__ = ["create_proposal_command"]
