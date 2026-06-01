from __future__ import annotations

from collections.abc import Callable

from src.api.services.workspace_errors import (
    WORKSPACE_EVALUATION_UNAVAILABLE_DETAIL,
    WorkspaceEvaluationUnavailableError,
    safe_workspace_error_detail,
)
from src.core.advisory.orchestration import evaluate_advisory_proposal
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposals.correlation import resolve_correlation_id
from src.core.workspace.evaluation import build_evaluation_summary
from src.core.workspace.reevaluation import (
    WorkspaceReevaluationContextError,
    build_workspace_evaluation_context,
)
from src.core.workspace.replay import build_replay_evidence
from src.core.workspace.session_models import WorkspaceSession

WorkspaceSimulateRequestBuilder = Callable[[WorkspaceSession], ProposalSimulateRequest]


def reevaluate_workspace_session_state(
    *,
    session: WorkspaceSession,
    simulate_request_builder: WorkspaceSimulateRequestBuilder,
) -> WorkspaceSession:
    simulate_request = simulate_request_builder(session)
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
    return session
