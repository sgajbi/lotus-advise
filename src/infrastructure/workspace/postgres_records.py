from __future__ import annotations

import json
from typing import Any, cast

from src.core.common.canonical import hash_canonical_payload
from src.core.workspace.session_models import WorkspaceSession
from src.core.workspace.version_models import WorkspaceSavedVersion
from src.core.workspace.versions import refresh_saved_version_metadata


def workspace_session_values(session: WorkspaceSession) -> tuple[Any, ...]:
    lifecycle_link = (
        session.lifecycle_link.model_dump(mode="json")
        if session.lifecycle_link is not None
        else None
    )
    return (
        session.workspace_id,
        session.workspace_name,
        session.input_mode,
        session.created_by,
        session.created_at,
        _updated_at(session),
        "ACTIVE",
        _resolved_context_hash(session),
        _latest_evaluation_request_hash(session),
        session.lifecycle_link.proposal_id if session.lifecycle_link else None,
        session.lifecycle_link.current_version_no if session.lifecycle_link else None,
        json_dump(lifecycle_link),
        json_dump(session.model_dump(mode="json")),
    )


def workspace_saved_version_values(
    *,
    workspace_id: str,
    saved_version: WorkspaceSavedVersion,
) -> tuple[Any, ...]:
    return (
        workspace_id,
        saved_version.workspace_version_id,
        saved_version.version_number,
        saved_version.saved_by,
        saved_version.saved_at,
        saved_version.replay_evidence.draft_state_hash,
        saved_version.replay_evidence.evaluation_request_hash,
        json_dump(saved_version.replay_evidence.model_dump(mode="json")),
        json_dump(saved_version.model_dump(mode="json")),
    )


def workspace_session_from_rows(
    *,
    session_row: dict[str, Any],
    saved_version_rows: list[dict[str, Any]],
) -> WorkspaceSession:
    payload = cast(dict[str, Any], json_load(session_row["session_json"]))
    payload["saved_versions"] = [json_load(row["saved_version_json"]) for row in saved_version_rows]
    session = cast(WorkspaceSession, WorkspaceSession.model_validate(payload))
    refresh_saved_version_metadata(session)
    return session


def json_dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def json_load(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _resolved_context_hash(session: WorkspaceSession) -> str | None:
    if session.resolved_context is None:
        return None
    return str(hash_canonical_payload(session.resolved_context.model_dump(mode="json")))


def _latest_evaluation_request_hash(session: WorkspaceSession) -> str | None:
    if session.latest_replay_evidence is None:
        return None
    return session.latest_replay_evidence.evaluation_request_hash


def _updated_at(session: WorkspaceSession) -> str:
    if session.latest_replay_evidence is not None:
        return session.latest_replay_evidence.captured_at
    if session.latest_saved_version is not None:
        return session.latest_saved_version.saved_at
    if session.lifecycle_link is not None:
        return session.lifecycle_link.last_handoff_at
    return session.created_at
