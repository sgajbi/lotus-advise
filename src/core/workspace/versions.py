from src.core.workspace.models import (
    WorkspaceSavedVersion,
    WorkspaceSavedVersionSummary,
    WorkspaceSession,
)


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
