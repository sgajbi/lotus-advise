from datetime import datetime, timezone
from uuid import uuid4

from src.core.workspace.models import (
    WorkspaceResolvedContext,
    WorkspaceSession,
    WorkspaceSessionCreateRequest,
    WorkspaceSessionCreateResponse,
    WorkspaceStatefulInput,
    WorkspaceStatelessInput,
)


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
    return WorkspaceResolvedContext(
        portfolio_id=stateful_input.portfolio_id,
        as_of=stateful_input.as_of,
    )


def create_workspace_session(
    request: WorkspaceSessionCreateRequest,
) -> WorkspaceSessionCreateResponse:
    if request.input_mode == "stateless":
        if request.stateless_input is None:
            raise ValueError("stateless workspace creation requires stateless_input")
        resolved_context = _build_stateless_resolved_context(request.stateless_input)
    else:
        if request.stateful_input is None:
            raise ValueError("stateful workspace creation requires stateful_input")
        resolved_context = _build_stateful_resolved_context(request.stateful_input)

    session = WorkspaceSession(
        workspace_id=f"aws_{uuid4().hex[:12]}",
        workspace_name=request.workspace_name,
        lifecycle_state="ACTIVE",
        input_mode=request.input_mode,
        created_by=request.created_by,
        created_at=_utc_now_iso(),
        stateless_input=request.stateless_input,
        stateful_input=request.stateful_input,
        resolved_context=resolved_context,
        evaluation_summary=None,
        latest_proposal_result=None,
    )
    return WorkspaceSessionCreateResponse(workspace=session)
