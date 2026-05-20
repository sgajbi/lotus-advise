from datetime import datetime, timezone
from typing import cast

from src.api.services.workspace_store import (
    DEFAULT_WORKSPACE_SESSION_CACHE_SIZE,
    WorkspaceNotFoundError,
    set_workspace_session_cache_size,
)
from src.api.services.workspace_store import (
    get_workspace_session as _get_workspace_session_from_store,
)
from src.api.services.workspace_store import (
    reset_workspace_sessions as _reset_workspace_sessions_in_store,
)
from src.api.services.workspace_store import (
    save_workspace_session as _save_workspace_session_to_store,
)
from src.core.advisory.orchestration import evaluate_advisory_proposal
from src.core.advisory.policy_context import ProposalPolicySelectors
from src.core.common.canonical import hash_canonical_payload
from src.core.models import ProposalSimulateRequest
from src.core.proposals import ProposalWorkflowService
from src.core.proposals.context import (
    ResolvedSimulationContext,
    build_context_resolution_evidence,
    canonicalize_simulation_request_payload,
)
from src.core.proposals.correlation import resolve_correlation_id
from src.core.proposals.models import ProposalCreateMetadata, ProposalResolvedContext
from src.core.replay.models import AdvisoryReplayEvidenceResponse
from src.core.replay.service import build_workspace_saved_version_replay_response
from src.core.workspace.compare import build_workspace_compare_response
from src.core.workspace.draft_actions import (
    WorkspaceDraftActionError,
    apply_workspace_draft_action_to_state,
)
from src.core.workspace.draft_state import (
    apply_workspace_draft_state,
    build_draft_state_from_simulate_request,
)
from src.core.workspace.evaluation import build_evaluation_summary
from src.core.workspace.handoff import (
    WorkspaceHandoffError,
    build_proposal_create_request,
    build_proposal_version_request,
    build_workspace_handoff_context_resolution,
    require_handoff_simulate_request,
)
from src.core.workspace.identifiers import (
    new_workspace_id,
    new_workspace_version_id,
)
from src.core.workspace.models import (
    WorkspaceCompareRequest,
    WorkspaceCompareResponse,
    WorkspaceDraftActionRequest,
    WorkspaceDraftActionResponse,
    WorkspaceDraftState,
    WorkspaceLifecycleHandoffRequest,
    WorkspaceLifecycleHandoffResponse,
    WorkspaceLifecycleLink,
    WorkspaceResolvedContext,
    WorkspaceResumeRequest,
    WorkspaceSavedVersion,
    WorkspaceSavedVersionListResponse,
    WorkspaceSaveRequest,
    WorkspaceSaveResponse,
    WorkspaceSession,
    WorkspaceSessionCreateRequest,
    WorkspaceSessionCreateResponse,
    WorkspaceStatefulInput,
    WorkspaceStatelessInput,
)
from src.core.workspace.replay import (
    apply_workspace_handoff_replay_lineage,
    build_replay_evidence,
    build_workspace_handoff_replay_lineage,
)
from src.core.workspace.sessions import build_workspace_session
from src.core.workspace.versions import (
    WorkspaceSavedVersionLookupError,
    apply_saved_workspace_version,
    build_saved_version_list_response,
    build_saved_workspace_version,
    find_saved_version,
    refresh_saved_version_metadata,
)
from src.integrations.lotus_core import (
    LotusCoreContextResolutionError,
    resolve_lotus_core_advisory_context,
)
from src.integrations.lotus_core.stateful_context import (
    enrich_stateful_simulate_request_for_trade_drafts,
)

MAX_WORKSPACE_SESSION_CACHE_SIZE = DEFAULT_WORKSPACE_SESSION_CACHE_SIZE


class WorkspaceEvaluationUnavailableError(Exception):
    pass


class WorkspaceSavedVersionNotFoundError(Exception):
    pass


class WorkspaceLifecycleHandoffUnavailableError(Exception):
    pass


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _current_business_date_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _build_stateless_resolved_context(
    stateless_input: WorkspaceStatelessInput,
) -> WorkspaceResolvedContext:
    simulate_request = stateless_input.simulate_request
    return WorkspaceResolvedContext(
        portfolio_id=simulate_request.portfolio_snapshot.portfolio_id,
        as_of=simulate_request.reference_model.as_of
        if simulate_request.reference_model is not None
        else _current_business_date_iso(),
        portfolio_snapshot_id=simulate_request.portfolio_snapshot.snapshot_id,
        market_data_snapshot_id=simulate_request.market_data_snapshot.snapshot_id,
    )


def _build_stateful_resolved_context(
    stateful_input: WorkspaceStatefulInput,
) -> WorkspaceResolvedContext:
    try:
        return cast(
            WorkspaceResolvedContext,
            resolve_lotus_core_advisory_context(stateful_input).resolved_context,
        )
    except LotusCoreContextResolutionError:
        return WorkspaceResolvedContext(
            portfolio_id=stateful_input.portfolio_id,
            as_of=stateful_input.as_of,
        )


def _build_simulate_request_for_workspace(session: WorkspaceSession) -> ProposalSimulateRequest:
    if session.input_mode == "stateful":
        if session.stateful_input is None:
            raise WorkspaceEvaluationUnavailableError("WORKSPACE_STATEFUL_INPUT_MISSING")
        try:
            resolved_stateful_context = resolve_lotus_core_advisory_context(session.stateful_input)
        except LotusCoreContextResolutionError as exc:
            raise WorkspaceEvaluationUnavailableError(
                "WORKSPACE_STATEFUL_CONTEXT_RESOLUTION_UNAVAILABLE"
            ) from exc
        session.resolved_context = resolved_stateful_context.resolved_context
        return enrich_stateful_simulate_request_for_trade_drafts(
            simulate_request=apply_workspace_draft_state(
                base_request=resolved_stateful_context.simulate_request,
                draft_state=session.draft_state,
            ),
            as_of=session.resolved_context.as_of,
        )

    if session.stateless_input is None:
        raise WorkspaceEvaluationUnavailableError("WORKSPACE_STATELESS_INPUT_MISSING")

    return apply_workspace_draft_state(
        base_request=session.stateless_input.simulate_request,
        draft_state=session.draft_state,
    )


def reevaluate_workspace_session(workspace_id: str) -> WorkspaceSession:
    session = get_workspace_session(workspace_id)
    simulate_request = _build_simulate_request_for_workspace(session)
    if session.resolved_context is None:
        raise WorkspaceEvaluationUnavailableError("WORKSPACE_RESOLVED_CONTEXT_MISSING")
    proposal_resolved_context = ProposalResolvedContext.model_validate(
        session.resolved_context.model_dump(mode="json")
    )
    resolved_request = ResolvedSimulationContext(
        input_mode=session.input_mode,
        resolution_source="LOTUS_CORE" if session.input_mode == "stateful" else "DIRECT_REQUEST",
        simulate_request=simulate_request,
        resolved_context=proposal_resolved_context,
        policy_selectors=ProposalPolicySelectors(
            household_id=(
                session.stateful_input.household_id if session.stateful_input is not None else None
            ),
            mandate_id=(
                session.stateful_input.mandate_id if session.stateful_input is not None else None
            ),
            benchmark_id=(
                session.stateful_input.benchmark_id if session.stateful_input is not None else None
            ),
        ),
        used_legacy_contract=False,
    )
    context_resolution = build_context_resolution_evidence(resolved_request)
    request_hash = hash_canonical_payload(
        canonicalize_simulation_request_payload(resolved=resolved_request)
    )
    correlation_id = resolve_correlation_id(None)
    result = evaluate_advisory_proposal(
        request=simulate_request,
        request_hash=request_hash,
        idempotency_key=None,
        correlation_id=correlation_id,
        resolved_as_of=proposal_resolved_context.as_of,
        policy_context=context_resolution["advisory_policy_context"],
    )
    result.explanation["context_resolution"] = context_resolution
    session.latest_proposal_result = result
    session.evaluation_summary = build_evaluation_summary(result, session)
    session.latest_replay_evidence = build_replay_evidence(
        session,
        evaluation_request_hash=request_hash,
    )
    _save_workspace_session(session)
    return session


def _save_workspace_session(session: WorkspaceSession) -> None:
    set_workspace_session_cache_size(MAX_WORKSPACE_SESSION_CACHE_SIZE)
    _save_workspace_session_to_store(session)


def get_workspace_session(workspace_id: str) -> WorkspaceSession:
    return _get_workspace_session_from_store(workspace_id)


def reset_workspace_sessions_for_tests() -> None:
    _reset_workspace_sessions_in_store()


def _find_saved_version(
    session: WorkspaceSession,
    workspace_version_id: str,
) -> WorkspaceSavedVersion:
    try:
        return find_saved_version(session, workspace_version_id)
    except WorkspaceSavedVersionLookupError as exc:
        raise WorkspaceSavedVersionNotFoundError("WORKSPACE_SAVED_VERSION_NOT_FOUND") from exc


def create_workspace_session(
    request: WorkspaceSessionCreateRequest,
) -> WorkspaceSessionCreateResponse:
    if request.input_mode == "stateless":
        if request.stateless_input is None:
            raise ValueError("stateless workspace creation requires stateless_input")
        resolved_context = _build_stateless_resolved_context(request.stateless_input)
        draft_state = build_draft_state_from_simulate_request(
            request.stateless_input.simulate_request
        )
    else:
        if request.stateful_input is None:
            raise ValueError("stateful workspace creation requires stateful_input")
        try:
            resolved_stateful_context = resolve_lotus_core_advisory_context(request.stateful_input)
        except LotusCoreContextResolutionError:
            resolved_context = WorkspaceResolvedContext(
                portfolio_id=request.stateful_input.portfolio_id,
                as_of=request.stateful_input.as_of,
            )
            draft_state = WorkspaceDraftState()
        else:
            resolved_context = resolved_stateful_context.resolved_context
            draft_state = build_draft_state_from_simulate_request(
                resolved_stateful_context.simulate_request
            )

    session = build_workspace_session(
        request=request,
        workspace_id=new_workspace_id(),
        created_at=_utc_now_iso(),
        draft_state=draft_state,
        resolved_context=resolved_context,
    )
    _save_workspace_session(session)
    return WorkspaceSessionCreateResponse(workspace=session)


def apply_workspace_draft_action(
    workspace_id: str,
    request: WorkspaceDraftActionRequest,
) -> WorkspaceDraftActionResponse:
    session = get_workspace_session(workspace_id)
    try:
        apply_workspace_draft_action_to_state(
            draft_state=session.draft_state,
            request=request,
        )
    except WorkspaceDraftActionError as exc:
        raise WorkspaceNotFoundError(str(exc)) from exc

    _save_workspace_session(session)
    updated_session = reevaluate_workspace_session(workspace_id)
    return WorkspaceDraftActionResponse(workspace=updated_session)


def save_workspace_version(
    workspace_id: str,
    request: WorkspaceSaveRequest,
) -> WorkspaceSaveResponse:
    session = get_workspace_session(workspace_id)
    saved_version = build_saved_workspace_version(
        session=session,
        request=request,
        workspace_version_id=new_workspace_version_id(),
        saved_at=_utc_now_iso(),
    )
    session.saved_versions.append(saved_version)
    refresh_saved_version_metadata(session)
    _save_workspace_session(session)
    return WorkspaceSaveResponse(workspace=session, saved_version=saved_version)


def list_workspace_saved_versions(
    workspace_id: str,
) -> WorkspaceSavedVersionListResponse:
    session = get_workspace_session(workspace_id)
    return build_saved_version_list_response(session)


def get_workspace_saved_version_replay(
    workspace_id: str,
    workspace_version_id: str,
) -> AdvisoryReplayEvidenceResponse:
    session = get_workspace_session(workspace_id)
    saved_version = _find_saved_version(session, workspace_version_id)
    return build_workspace_saved_version_replay_response(
        session=session,
        saved_version=saved_version,
    )


def resume_workspace_version(
    workspace_id: str,
    request: WorkspaceResumeRequest,
) -> WorkspaceSession:
    session = get_workspace_session(workspace_id)
    saved_version = _find_saved_version(session, request.workspace_version_id)
    apply_saved_workspace_version(session=session, saved_version=saved_version)
    _save_workspace_session(session)
    return session


def compare_workspace_to_saved_version(
    workspace_id: str,
    request: WorkspaceCompareRequest,
) -> WorkspaceCompareResponse:
    session = get_workspace_session(workspace_id)
    saved_version = _find_saved_version(session, request.workspace_version_id)
    return build_workspace_compare_response(
        session=session,
        baseline_version=saved_version,
    )


def handoff_workspace_to_proposal_lifecycle(
    workspace_id: str,
    request: WorkspaceLifecycleHandoffRequest,
    proposal_service: ProposalWorkflowService,
    idempotency_key: str | None,
    correlation_id: str | None,
) -> WorkspaceLifecycleHandoffResponse:
    session = get_workspace_session(workspace_id)
    try:
        if session.lifecycle_link is None:
            if not idempotency_key:
                raise WorkspaceLifecycleHandoffUnavailableError(
                    "WORKSPACE_HANDOFF_IDEMPOTENCY_KEY_REQUIRED"
                )
            create_request = build_proposal_create_request(
                session,
                request,
                _build_simulate_request_for_workspace(session),
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
            handoff_action = "CREATED_PROPOSAL"
        else:
            version_request = build_proposal_version_request(
                session,
                request,
                _build_simulate_request_for_workspace(session),
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
            handoff_action = "CREATED_PROPOSAL_VERSION"
    except (ValueError, WorkspaceEvaluationUnavailableError, WorkspaceHandoffError) as exc:
        raise WorkspaceLifecycleHandoffUnavailableError(str(exc)) from exc

    replay_lineage["proposal_id"] = proposal_response.proposal.proposal_id
    replay_lineage["proposal_version_no"] = proposal_response.version.version_no
    apply_workspace_handoff_replay_lineage(session, replay_lineage)
    session.lifecycle_link = WorkspaceLifecycleLink(
        proposal_id=proposal_response.proposal.proposal_id,
        current_version_no=proposal_response.version.version_no,
        last_handoff_at=_utc_now_iso(),
        last_handoff_by=request.handoff_by,
    )
    _save_workspace_session(session)
    return WorkspaceLifecycleHandoffResponse(
        workspace=session,
        handoff_action=handoff_action,
        proposal=proposal_response,
    )
