from __future__ import annotations

from typing import cast

from src.api.services import workspace_store
from src.api.services.workspace_errors import WorkspaceSavedVersionNotFoundError
from src.core.replay.models import AdvisoryReplayEvidenceResponse
from src.core.replay.service import build_workspace_saved_version_replay_response
from src.core.workspace.compare import build_workspace_compare_response
from src.core.workspace.identifiers import new_workspace_version_id
from src.core.workspace.models import (
    WorkspaceCompareRequest,
    WorkspaceCompareResponse,
    WorkspaceResumeRequest,
    WorkspaceSavedVersionListResponse,
    WorkspaceSaveRequest,
    WorkspaceSaveResponse,
    WorkspaceSession,
)
from src.core.workspace.version_models import WorkspaceSavedVersion
from src.core.workspace.versions import (
    WorkspaceSavedVersionLookupError,
    apply_saved_workspace_version,
    build_saved_version_list_response,
    build_saved_workspace_version,
    find_saved_version,
    refresh_saved_version_metadata,
)


def save_workspace_version(
    workspace_id: str,
    request: WorkspaceSaveRequest,
    *,
    saved_at: str,
) -> WorkspaceSaveResponse:
    session = workspace_store.get_workspace_session(workspace_id)
    saved_version = build_saved_workspace_version(
        session=session,
        request=request,
        workspace_version_id=new_workspace_version_id(),
        saved_at=saved_at,
    )
    session.saved_versions.append(saved_version)
    refresh_saved_version_metadata(session)
    _save_workspace_session(session)
    return WorkspaceSaveResponse(workspace=session, saved_version=saved_version)


def list_workspace_saved_versions(
    workspace_id: str,
) -> WorkspaceSavedVersionListResponse:
    session = workspace_store.get_workspace_session(workspace_id)
    return build_saved_version_list_response(session)


def get_workspace_saved_version_replay(
    workspace_id: str,
    workspace_version_id: str,
) -> AdvisoryReplayEvidenceResponse:
    session = workspace_store.get_workspace_session(workspace_id)
    saved_version = _find_saved_version(session, workspace_version_id)
    return build_workspace_saved_version_replay_response(
        session=session,
        saved_version=saved_version,
    )


def resume_workspace_version(
    workspace_id: str,
    request: WorkspaceResumeRequest,
) -> WorkspaceSession:
    session = workspace_store.get_workspace_session(workspace_id)
    saved_version = _find_saved_version(session, request.workspace_version_id)
    apply_saved_workspace_version(session=session, saved_version=saved_version)
    _save_workspace_session(session)
    return cast(WorkspaceSession, session)


def compare_workspace_to_saved_version(
    workspace_id: str,
    request: WorkspaceCompareRequest,
) -> WorkspaceCompareResponse:
    session = workspace_store.get_workspace_session(workspace_id)
    saved_version = _find_saved_version(session, request.workspace_version_id)
    return build_workspace_compare_response(
        session=session,
        baseline_version=saved_version,
    )


def _find_saved_version(
    session: WorkspaceSession,
    workspace_version_id: str,
) -> WorkspaceSavedVersion:
    try:
        return find_saved_version(session, workspace_version_id)
    except WorkspaceSavedVersionLookupError as exc:
        raise WorkspaceSavedVersionNotFoundError("WORKSPACE_SAVED_VERSION_NOT_FOUND") from exc


def _save_workspace_session(session: WorkspaceSession) -> None:
    workspace_store.set_workspace_session_cache_size(
        workspace_store.DEFAULT_WORKSPACE_SESSION_CACHE_SIZE
    )
    workspace_store.save_workspace_session(session)
