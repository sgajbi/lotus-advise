from datetime import datetime, timezone
from typing import Any, Protocol, cast

from src.core.advisory.risk_lens import extract_risk_lens
from src.core.common.canonical import hash_canonical_payload
from src.core.workspace.models import (
    WorkspaceLifecycleHandoffRequest,
    WorkspaceReplayEvidence,
    WorkspaceSavedVersion,
    WorkspaceSession,
)


class _ProposalResultWithExplanation(Protocol):
    explanation: dict[str, Any]


def build_draft_state_hash(session: WorkspaceSession) -> str:
    return cast(str, hash_canonical_payload(session.draft_state.model_dump(mode="json")))


def build_replay_evidence(
    session: WorkspaceSession,
    evaluation_request_hash: str | None = None,
) -> WorkspaceReplayEvidence:
    return WorkspaceReplayEvidence(
        input_mode=session.input_mode,
        resolved_context=(
            session.resolved_context.model_copy(deep=True)
            if session.resolved_context is not None
            else None
        ),
        draft_state_hash=build_draft_state_hash(session),
        evaluation_request_hash=evaluation_request_hash,
        captured_at=_utc_now_iso(),
        continuity={},
        risk_lens=(
            extract_risk_lens(cast(_ProposalResultWithExplanation, session.latest_proposal_result))
            if session.latest_proposal_result is not None
            else None
        ),
    )


def find_matching_saved_version(session: WorkspaceSession) -> WorkspaceSavedVersion | None:
    draft_state_hash = build_draft_state_hash(session)
    evaluation_request_hash = (
        session.latest_replay_evidence.evaluation_request_hash
        if session.latest_replay_evidence is not None
        else None
    )
    for saved_version in reversed(session.saved_versions):
        if saved_version.replay_evidence.draft_state_hash != draft_state_hash:
            continue
        if (
            evaluation_request_hash is not None
            and saved_version.replay_evidence.evaluation_request_hash != evaluation_request_hash
        ):
            continue
        return saved_version
    return None


def build_workspace_handoff_replay_lineage(
    session: WorkspaceSession,
    request: WorkspaceLifecycleHandoffRequest,
    handoff_action: str,
    proposal_id: str,
    proposal_version_no: int,
) -> dict[str, str | int | None]:
    matched_saved_version = find_matching_saved_version(session)
    return {
        "workspace_id": session.workspace_id,
        "workspace_version_id": (
            matched_saved_version.workspace_version_id
            if matched_saved_version is not None
            else None
        ),
        "draft_state_hash": build_draft_state_hash(session),
        "evaluation_request_hash": (
            session.latest_replay_evidence.evaluation_request_hash
            if session.latest_replay_evidence is not None
            else None
        ),
        "handoff_action": handoff_action,
        "handoff_at": _utc_now_iso(),
        "handoff_by": request.handoff_by,
        "proposal_id": proposal_id,
        "proposal_version_no": proposal_version_no,
    }


def apply_workspace_handoff_replay_lineage(
    session: WorkspaceSession,
    replay_lineage: dict[str, str | int | None],
) -> None:
    if session.latest_replay_evidence is not None:
        session.latest_replay_evidence.continuity = dict(replay_lineage)
    matched_saved_version = find_matching_saved_version(session)
    if matched_saved_version is not None:
        matched_saved_version.replay_evidence.continuity = dict(replay_lineage)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
