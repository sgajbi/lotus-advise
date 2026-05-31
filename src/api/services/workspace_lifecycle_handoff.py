from collections.abc import Callable

from src.api.services.workspace_errors import (
    WorkspaceEvaluationUnavailableError,
    WorkspaceLifecycleHandoffUnavailableError,
)
from src.core.common.idempotency import normalize_required_idempotency_key
from src.core.models import ProposalSimulateRequest
from src.core.proposals import ProposalWorkflowService
from src.core.proposals.models import ProposalCreateMetadata, ProposalCreateResponse
from src.core.workspace.handoff import (
    WorkspaceHandoffError,
    build_proposal_create_request,
    build_proposal_version_request,
    build_workspace_handoff_context_resolution,
    complete_workspace_lifecycle_handoff,
    require_handoff_simulate_request,
)
from src.core.workspace.models import (
    WorkspaceLifecycleHandoffRequest,
    WorkspaceLifecycleHandoffResponse,
    WorkspaceSession,
)
from src.core.workspace.replay import build_workspace_handoff_replay_lineage

WorkspaceSimulateRequestBuilder = Callable[[WorkspaceSession], ProposalSimulateRequest]
WorkspaceLifecycleHandoffExecution = tuple[
    ProposalCreateResponse,
    dict[str, str | int | None],
    str,
]


def execute_workspace_lifecycle_handoff(
    *,
    workspace_id: str,
    session: WorkspaceSession,
    request: WorkspaceLifecycleHandoffRequest,
    proposal_service: ProposalWorkflowService,
    idempotency_key: str | None,
    correlation_id: str | None,
    simulate_request_builder: WorkspaceSimulateRequestBuilder,
    completed_at: str,
) -> WorkspaceLifecycleHandoffResponse:
    try:
        if session.lifecycle_link is None:
            proposal_response, replay_lineage, handoff_action = _create_proposal_from_workspace(
                workspace_id=workspace_id,
                session=session,
                request=request,
                proposal_service=proposal_service,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                simulate_request_builder=simulate_request_builder,
            )
        else:
            (
                proposal_response,
                replay_lineage,
                handoff_action,
            ) = _create_proposal_version_from_workspace(
                session=session,
                request=request,
                proposal_service=proposal_service,
                correlation_id=correlation_id,
                simulate_request_builder=simulate_request_builder,
            )
    except (ValueError, WorkspaceEvaluationUnavailableError, WorkspaceHandoffError) as exc:
        raise WorkspaceLifecycleHandoffUnavailableError(str(exc)) from exc

    return complete_workspace_lifecycle_handoff(
        session=session,
        request=request,
        proposal_response=proposal_response,
        replay_lineage=replay_lineage,
        handoff_action=handoff_action,
        completed_at=completed_at,
    )


def _create_proposal_from_workspace(
    *,
    workspace_id: str,
    session: WorkspaceSession,
    request: WorkspaceLifecycleHandoffRequest,
    proposal_service: ProposalWorkflowService,
    idempotency_key: str | None,
    correlation_id: str | None,
    simulate_request_builder: WorkspaceSimulateRequestBuilder,
) -> WorkspaceLifecycleHandoffExecution:
    try:
        idempotency_key = normalize_required_idempotency_key(idempotency_key)
    except ValueError as exc:
        raise WorkspaceLifecycleHandoffUnavailableError(
            "WORKSPACE_HANDOFF_IDEMPOTENCY_KEY_REQUIRED"
        ) from exc
    create_request = build_proposal_create_request(
        session,
        request,
        simulate_request_builder(session),
    )
    replay_lineage = build_workspace_handoff_replay_lineage(
        session,
        request,
        "CREATED_PROPOSAL",
        proposal_id="",
        proposal_version_no=1,
    )
    proposal_response = proposal_service.create_proposal(
        payload=create_request,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        lifecycle_origin="WORKSPACE_HANDOFF",
        source_workspace_id=workspace_id,
        replay_lineage=replay_lineage,
        context_resolution_override=build_workspace_handoff_context_resolution(
            session,
            require_handoff_simulate_request(create_request.simulate_request),
            create_request.metadata,
        ),
    )
    return proposal_response, replay_lineage, "CREATED_PROPOSAL"


def _create_proposal_version_from_workspace(
    *,
    session: WorkspaceSession,
    request: WorkspaceLifecycleHandoffRequest,
    proposal_service: ProposalWorkflowService,
    correlation_id: str | None,
    simulate_request_builder: WorkspaceSimulateRequestBuilder,
) -> WorkspaceLifecycleHandoffExecution:
    if session.lifecycle_link is None:
        raise WorkspaceLifecycleHandoffUnavailableError("WORKSPACE_HANDOFF_LINK_MISSING")
    version_request = build_proposal_version_request(
        session,
        request,
        simulate_request_builder(session),
    )
    replay_lineage = build_workspace_handoff_replay_lineage(
        session,
        request,
        "CREATED_PROPOSAL_VERSION",
        proposal_id=session.lifecycle_link.proposal_id,
        proposal_version_no=session.lifecycle_link.current_version_no + 1,
    )
    proposal_response = proposal_service.create_version(
        proposal_id=session.lifecycle_link.proposal_id,
        payload=version_request,
        correlation_id=correlation_id,
        replay_lineage=replay_lineage,
        context_resolution_override=build_workspace_handoff_context_resolution(
            session,
            require_handoff_simulate_request(version_request.simulate_request),
            ProposalCreateMetadata(),
        ),
    )
    return proposal_response, replay_lineage, "CREATED_PROPOSAL_VERSION"
