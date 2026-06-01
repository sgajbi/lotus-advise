from datetime import datetime, timezone

from src.api.services.workspace_context_resolution import (
    build_initial_workspace_context,
    build_workspace_simulate_request,
)
from src.api.services.workspace_errors import (
    WORKSPACE_DRAFT_ACTION_INVALID_DETAIL,
    WORKSPACE_EVALUATION_UNAVAILABLE_DETAIL,
    WorkspaceEvaluationUnavailableError,
    WorkspaceNotFoundError,
    WorkspaceSavedVersionNotFoundError,
    safe_workspace_error_detail,
)
from src.api.services.workspace_errors import (
    WorkspaceLifecycleHandoffUnavailableError as WorkspaceLifecycleHandoffUnavailableError,
)
from src.api.services.workspace_lifecycle_handoff import execute_workspace_lifecycle_handoff
from src.api.services.workspace_store import (
    DEFAULT_WORKSPACE_SESSION_CACHE_SIZE,
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
from src.core.models import ProposalSimulateRequest
from src.core.proposals import ProposalWorkflowService
from src.core.proposals.correlation import resolve_correlation_id
from src.core.replay.models import AdvisoryReplayEvidenceResponse
from src.core.replay.service import build_workspace_saved_version_replay_response
from src.core.workspace.compare import build_workspace_compare_response
from src.core.workspace.draft_actions import (
    WorkspaceDraftActionError,
    apply_workspace_draft_action_to_state,
)
from src.core.workspace.evaluation import build_evaluation_summary
from src.core.workspace.identifiers import (
    new_workspace_id,
    new_workspace_version_id,
)
from src.core.workspace.models import (
    WorkspaceCompareRequest,
    WorkspaceCompareResponse,
    WorkspaceDraftActionRequest,
    WorkspaceDraftActionResponse,
    WorkspaceLifecycleHandoffRequest,
    WorkspaceLifecycleHandoffResponse,
    WorkspaceResumeRequest,
    WorkspaceSavedVersion,
    WorkspaceSavedVersionListResponse,
    WorkspaceSaveRequest,
    WorkspaceSaveResponse,
    WorkspaceSession,
    WorkspaceSessionCreateRequest,
    WorkspaceSessionCreateResponse,
)
from src.core.workspace.reevaluation import (
    WorkspaceReevaluationContextError,
    build_workspace_evaluation_context,
)
from src.core.workspace.replay import build_replay_evidence
from src.core.workspace.sessions import build_workspace_session
from src.core.workspace.versions import (
    WorkspaceSavedVersionLookupError,
    apply_saved_workspace_version,
    build_saved_version_list_response,
    build_saved_workspace_version,
    find_saved_version,
    refresh_saved_version_metadata,
)

MAX_WORKSPACE_SESSION_CACHE_SIZE = DEFAULT_WORKSPACE_SESSION_CACHE_SIZE


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _current_business_date_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _build_simulate_request_for_workspace(session: WorkspaceSession) -> ProposalSimulateRequest:
    return build_workspace_simulate_request(session)


def reevaluate_workspace_session(workspace_id: str) -> WorkspaceSession:
    session = get_workspace_session(workspace_id)
    simulate_request = _build_simulate_request_for_workspace(session)
    try:
        evaluation_context = build_workspace_evaluation_context(
            session=session,
            simulate_request=simulate_request,
        )
    except WorkspaceReevaluationContextError as exc:
        raise WorkspaceEvaluationUnavailableError(
            safe_workspace_error_detail(
                str(exc),
                fallback=WORKSPACE_EVALUATION_UNAVAILABLE_DETAIL,
            )
        ) from exc
    correlation_id = resolve_correlation_id(None)
    result = evaluate_advisory_proposal(
        request=simulate_request,
        request_hash=evaluation_context.request_hash,
        idempotency_key=None,
        correlation_id=correlation_id,
        resolved_as_of=evaluation_context.resolved_request.resolved_context.as_of,
        input_mode=evaluation_context.resolved_request.input_mode,
        policy_context=evaluation_context.context_resolution["advisory_policy_context"],
    )
    result.explanation["context_resolution"] = evaluation_context.context_resolution
    session.latest_proposal_result = result
    session.evaluation_summary = build_evaluation_summary(result, session)
    session.latest_replay_evidence = build_replay_evidence(
        session,
        evaluation_request_hash=evaluation_context.request_hash,
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
    resolved_context, draft_state = build_initial_workspace_context(
        request=request,
        fallback_as_of=_current_business_date_iso(),
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
        raise WorkspaceNotFoundError(
            safe_workspace_error_detail(
                str(exc),
                fallback=WORKSPACE_DRAFT_ACTION_INVALID_DETAIL,
            )
        ) from exc

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
    response = execute_workspace_lifecycle_handoff(
        workspace_id=workspace_id,
        session=session,
        request=request,
        proposal_service=proposal_service,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        simulate_request_builder=_build_simulate_request_for_workspace,
        completed_at=_utc_now_iso(),
    )
    _save_workspace_session(session)
    return response
