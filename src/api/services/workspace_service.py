from collections import OrderedDict
from datetime import datetime, timezone
from decimal import Decimal
from typing import OrderedDict as OrderedDictType
from uuid import uuid4

from src.core.advisory_engine import run_proposal_simulation
from src.core.common.canonical import hash_canonical_payload
from src.core.models import ProposalResult, ProposalSimulateRequest, RuleResult
from src.core.workspace.models import (
    WorkspaceCashFlowDraft,
    WorkspaceDraftActionRequest,
    WorkspaceDraftActionResponse,
    WorkspaceDraftState,
    WorkspaceEvaluationImpactSummary,
    WorkspaceEvaluationSummary,
    WorkspaceResolvedContext,
    WorkspaceSession,
    WorkspaceSessionCreateRequest,
    WorkspaceSessionCreateResponse,
    WorkspaceStatefulInput,
    WorkspaceStatelessInput,
    WorkspaceTradeDraft,
)

MAX_WORKSPACE_SESSION_CACHE_SIZE = 500
WORKSPACE_SESSIONS: "OrderedDictType[str, WorkspaceSession]" = OrderedDict()


class WorkspaceNotFoundError(Exception):
    pass


class WorkspaceEvaluationUnavailableError(Exception):
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
    return WorkspaceResolvedContext(
        portfolio_id=stateful_input.portfolio_id,
        as_of=stateful_input.as_of,
    )


def _build_initial_draft_state(request: WorkspaceSessionCreateRequest) -> WorkspaceDraftState:
    if request.input_mode == "stateless":
        assert request.stateless_input is not None
        simulate_request = request.stateless_input.simulate_request
        return WorkspaceDraftState(
            options=simulate_request.options.model_copy(deep=True),
            reference_model=(
                simulate_request.reference_model.model_copy(deep=True)
                if simulate_request.reference_model is not None
                else None
            ),
            trade_drafts=[
                WorkspaceTradeDraft(
                    workspace_trade_id=f"wtd_{uuid4().hex[:12]}",
                    trade=trade.model_copy(deep=True),
                )
                for trade in simulate_request.proposed_trades
            ],
            cash_flow_drafts=[
                WorkspaceCashFlowDraft(
                    workspace_cash_flow_id=f"wcf_{uuid4().hex[:12]}",
                    cash_flow=cash_flow.model_copy(deep=True),
                )
                for cash_flow in simulate_request.proposed_cash_flows
            ],
        )

    return WorkspaceDraftState()


def _build_simulate_request_for_workspace(session: WorkspaceSession) -> ProposalSimulateRequest:
    if session.input_mode != "stateless" or session.stateless_input is None:
        raise WorkspaceEvaluationUnavailableError("WORKSPACE_STATEFUL_EVALUATION_NOT_IMPLEMENTED")

    source_request = session.stateless_input.simulate_request
    return ProposalSimulateRequest(
        portfolio_snapshot=source_request.portfolio_snapshot.model_copy(deep=True),
        market_data_snapshot=source_request.market_data_snapshot.model_copy(deep=True),
        shelf_entries=[entry.model_copy(deep=True) for entry in source_request.shelf_entries],
        options=session.draft_state.options.model_copy(deep=True),
        proposed_cash_flows=[
            draft.cash_flow.model_copy(deep=True) for draft in session.draft_state.cash_flow_drafts
        ],
        proposed_trades=[
            draft.trade.model_copy(deep=True) for draft in session.draft_state.trade_drafts
        ],
        reference_model=(
            session.draft_state.reference_model.model_copy(deep=True)
            if session.draft_state.reference_model is not None
            else None
        ),
    )


def _calculate_review_issue_count(result: ProposalResult) -> int:
    soft_fail_count = sum(
        1
        for rule_result in result.rule_results
        if rule_result.status == "FAIL" and rule_result.severity == "SOFT"
    )
    suitability_issue_count = len(result.suitability.issues) if result.suitability is not None else 0
    return soft_fail_count + suitability_issue_count


def _calculate_blocking_issue_count(result: ProposalResult) -> int:
    return sum(
        1
        for rule_result in result.rule_results
        if rule_result.status == "FAIL" and rule_result.severity == "HARD"
    )


def _format_portfolio_delta(result: ProposalResult) -> str:
    if result.reconciliation is not None:
        return str(result.reconciliation.delta.amount)
    delta = result.after_simulated.total_value.amount - result.before.total_value.amount
    return str(delta.quantize(Decimal("0.01")))


def _build_evaluation_summary(result: ProposalResult, session: WorkspaceSession) -> WorkspaceEvaluationSummary:
    return WorkspaceEvaluationSummary(
        status=result.status,
        gate_decision=result.gate_decision.model_copy(deep=True) if result.gate_decision else None,
        blocking_issue_count=_calculate_blocking_issue_count(result),
        review_issue_count=_calculate_review_issue_count(result),
        impact_summary=WorkspaceEvaluationImpactSummary(
            portfolio_value_delta_base_ccy=_format_portfolio_delta(result),
            trade_count=len(session.draft_state.trade_drafts),
            cash_flow_count=len(session.draft_state.cash_flow_drafts),
        ),
    )


def reevaluate_workspace_session(workspace_id: str) -> WorkspaceSession:
    session = get_workspace_session(workspace_id)
    simulate_request = _build_simulate_request_for_workspace(session)
    request_payload = simulate_request.model_dump(mode="json")
    request_hash = hash_canonical_payload(request_payload)
    correlation_id = f"corr_{uuid4().hex[:12]}"
    result = run_proposal_simulation(
        portfolio=simulate_request.portfolio_snapshot,
        market_data=simulate_request.market_data_snapshot,
        shelf=simulate_request.shelf_entries,
        options=simulate_request.options,
        proposed_cash_flows=simulate_request.proposed_cash_flows,
        proposed_trades=simulate_request.proposed_trades,
        reference_model=simulate_request.reference_model,
        request_hash=request_hash,
        idempotency_key=None,
        correlation_id=correlation_id,
    )
    session.latest_proposal_result = result
    session.evaluation_summary = _build_evaluation_summary(result, session)
    _save_workspace_session(session)
    return session


def _save_workspace_session(session: WorkspaceSession) -> None:
    WORKSPACE_SESSIONS[session.workspace_id] = session
    WORKSPACE_SESSIONS.move_to_end(session.workspace_id)
    while len(WORKSPACE_SESSIONS) > MAX_WORKSPACE_SESSION_CACHE_SIZE:
        WORKSPACE_SESSIONS.popitem(last=False)


def get_workspace_session(workspace_id: str) -> WorkspaceSession:
    session = WORKSPACE_SESSIONS.get(workspace_id)
    if session is None:
        raise WorkspaceNotFoundError("WORKSPACE_NOT_FOUND")
    return session


def reset_workspace_sessions_for_tests() -> None:
    WORKSPACE_SESSIONS.clear()


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
        draft_state=_build_initial_draft_state(request),
        resolved_context=resolved_context,
        evaluation_summary=None,
        latest_proposal_result=None,
    )
    _save_workspace_session(session)
    return WorkspaceSessionCreateResponse(workspace=session)


def apply_workspace_draft_action(
    workspace_id: str,
    request: WorkspaceDraftActionRequest,
) -> WorkspaceDraftActionResponse:
    session = get_workspace_session(workspace_id)
    draft_state = session.draft_state

    if request.action_type == "ADD_TRADE":
        assert request.trade is not None
        draft_state.trade_drafts.append(
            WorkspaceTradeDraft(
                workspace_trade_id=f"wtd_{uuid4().hex[:12]}",
                trade=request.trade.model_copy(deep=True),
            )
        )
    elif request.action_type == "UPDATE_TRADE":
        assert request.trade is not None and request.workspace_trade_id is not None
        trade_draft = next(
            (item for item in draft_state.trade_drafts if item.workspace_trade_id == request.workspace_trade_id),
            None,
        )
        if trade_draft is None:
            raise WorkspaceNotFoundError("WORKSPACE_TRADE_NOT_FOUND")
        trade_draft.trade = request.trade.model_copy(deep=True)
    elif request.action_type == "REMOVE_TRADE":
        assert request.workspace_trade_id is not None
        original_len = len(draft_state.trade_drafts)
        draft_state.trade_drafts = [
            item
            for item in draft_state.trade_drafts
            if item.workspace_trade_id != request.workspace_trade_id
        ]
        if len(draft_state.trade_drafts) == original_len:
            raise WorkspaceNotFoundError("WORKSPACE_TRADE_NOT_FOUND")
    elif request.action_type == "ADD_CASH_FLOW":
        assert request.cash_flow is not None
        draft_state.cash_flow_drafts.append(
            WorkspaceCashFlowDraft(
                workspace_cash_flow_id=f"wcf_{uuid4().hex[:12]}",
                cash_flow=request.cash_flow.model_copy(deep=True),
            )
        )
    elif request.action_type == "UPDATE_CASH_FLOW":
        assert request.cash_flow is not None and request.workspace_cash_flow_id is not None
        cash_flow_draft = next(
            (
                item
                for item in draft_state.cash_flow_drafts
                if item.workspace_cash_flow_id == request.workspace_cash_flow_id
            ),
            None,
        )
        if cash_flow_draft is None:
            raise WorkspaceNotFoundError("WORKSPACE_CASH_FLOW_NOT_FOUND")
        cash_flow_draft.cash_flow = request.cash_flow.model_copy(deep=True)
    elif request.action_type == "REMOVE_CASH_FLOW":
        assert request.workspace_cash_flow_id is not None
        original_len = len(draft_state.cash_flow_drafts)
        draft_state.cash_flow_drafts = [
            item
            for item in draft_state.cash_flow_drafts
            if item.workspace_cash_flow_id != request.workspace_cash_flow_id
        ]
        if len(draft_state.cash_flow_drafts) == original_len:
            raise WorkspaceNotFoundError("WORKSPACE_CASH_FLOW_NOT_FOUND")
    elif request.action_type == "REPLACE_OPTIONS":
        assert request.options is not None
        draft_state.options = request.options.model_copy(deep=True)

    _save_workspace_session(session)
    updated_session = reevaluate_workspace_session(workspace_id)
    return WorkspaceDraftActionResponse(workspace=updated_session)
