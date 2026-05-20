from src.core.workspace.models import (
    WorkspaceSavedVersion,
    WorkspaceSavedVersionSummary,
    WorkspaceSaveRequest,
    WorkspaceSession,
)
from src.core.workspace.replay import build_replay_evidence


class WorkspaceSavedVersionLookupError(ValueError):
    pass


def build_saved_version_summary(
    version: WorkspaceSavedVersion,
) -> WorkspaceSavedVersionSummary:
    return WorkspaceSavedVersionSummary(
        workspace_version_id=version.workspace_version_id,
        version_number=version.version_number,
        version_label=version.version_label,
        saved_by=version.saved_by,
        saved_at=version.saved_at,
    )


def refresh_saved_version_metadata(session: WorkspaceSession) -> None:
    session.saved_version_count = len(session.saved_versions)
    session.latest_saved_version = (
        build_saved_version_summary(session.saved_versions[-1]) if session.saved_versions else None
    )


def find_saved_version(
    session: WorkspaceSession,
    workspace_version_id: str,
) -> WorkspaceSavedVersion:
    saved_version = next(
        (
            item
            for item in session.saved_versions
            if item.workspace_version_id == workspace_version_id
        ),
        None,
    )
    if saved_version is None:
        raise WorkspaceSavedVersionLookupError("WORKSPACE_SAVED_VERSION_NOT_FOUND")
    return saved_version


def build_saved_workspace_version(
    *,
    session: WorkspaceSession,
    request: WorkspaceSaveRequest,
    workspace_version_id: str,
    saved_at: str,
) -> WorkspaceSavedVersion:
    replay_evidence = (
        session.latest_replay_evidence.model_copy(deep=True)
        if session.latest_replay_evidence is not None
        else build_replay_evidence(session)
    )
    return WorkspaceSavedVersion(
        workspace_version_id=workspace_version_id,
        version_number=len(session.saved_versions) + 1,
        version_label=request.version_label,
        saved_by=request.saved_by,
        saved_at=saved_at,
        draft_state=session.draft_state.model_copy(deep=True),
        evaluation_summary=(
            session.evaluation_summary.model_copy(deep=True)
            if session.evaluation_summary is not None
            else None
        ),
        latest_proposal_result=(
            session.latest_proposal_result.model_copy(deep=True)
            if session.latest_proposal_result is not None
            else None
        ),
        replay_evidence=replay_evidence,
    )


def apply_saved_workspace_version(
    *,
    session: WorkspaceSession,
    saved_version: WorkspaceSavedVersion,
) -> None:
    session.draft_state = saved_version.draft_state.model_copy(deep=True)
    session.evaluation_summary = (
        saved_version.evaluation_summary.model_copy(deep=True)
        if saved_version.evaluation_summary is not None
        else None
    )
    session.latest_proposal_result = (
        saved_version.latest_proposal_result.model_copy(deep=True)
        if saved_version.latest_proposal_result is not None
        else None
    )
    session.latest_replay_evidence = saved_version.replay_evidence.model_copy(deep=True)
