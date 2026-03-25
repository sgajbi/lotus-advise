from datetime import datetime, timezone
from uuid import uuid4

from src.core.workspace.models import (
    WorkspaceResolvedContext,
    WorkspaceSession,
    WorkspaceSessionCreateRequest,
    WorkspaceSessionCreateResponse,
)


def create_workspace_session(
    request: WorkspaceSessionCreateRequest,
) -> WorkspaceSessionCreateResponse:
    if request.input_mode == "stateless":
        assert request.stateless_input is not None
        simulate_request = request.stateless_input.simulate_request
        resolved_context = WorkspaceResolvedContext(
            portfolio_id=simulate_request.portfolio_snapshot.portfolio_id,
            as_of=simulate_request.reference_model.as_of
            if simulate_request.reference_model is not None
            else datetime.now(timezone.utc).date().isoformat(),
            portfolio_snapshot_id=simulate_request.portfolio_snapshot.snapshot_id,
            market_data_snapshot_id=simulate_request.market_data_snapshot.snapshot_id,
        )
    else:
        assert request.stateful_input is not None
        resolved_context = WorkspaceResolvedContext(
            portfolio_id=request.stateful_input.portfolio_id,
            as_of=request.stateful_input.as_of,
        )

    session = WorkspaceSession(
        workspace_id=f"aws_{uuid4().hex[:12]}",
        workspace_name=request.workspace_name,
        lifecycle_state="ACTIVE",
        input_mode=request.input_mode,
        created_by=request.created_by,
        created_at=datetime.now(timezone.utc).isoformat(),
        stateless_input=request.stateless_input,
        stateful_input=request.stateful_input,
        resolved_context=resolved_context,
        evaluation_summary=None,
        latest_proposal_result=None,
    )
    return WorkspaceSessionCreateResponse(workspace=session)
