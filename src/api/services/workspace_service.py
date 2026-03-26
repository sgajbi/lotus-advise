from collections import OrderedDict
from datetime import datetime, timezone
from decimal import Decimal
from typing import OrderedDict as OrderedDictType
from uuid import uuid4

from src.core.advisory.orchestration import evaluate_advisory_proposal
from src.core.common.canonical import hash_canonical_payload
from src.core.models import ProposalResult, ProposalSimulateRequest
from src.core.proposals import (
    ProposalCreateRequest,
    ProposalVersionRequest,
    ProposalWorkflowService,
)
from src.core.proposals.models import ProposalCreateMetadata
from src.core.workspace.models import (
    WorkspaceCashFlowDraft,
    WorkspaceCompareDiffSummary,
    WorkspaceCompareRequest,
    WorkspaceCompareResponse,
    WorkspaceDraftActionRequest,
    WorkspaceDraftActionResponse,
    WorkspaceDraftState,
    WorkspaceEvaluationImpactSummary,
    WorkspaceEvaluationSummary,
    WorkspaceLifecycleHandoffRequest,
    WorkspaceLifecycleHandoffResponse,
    WorkspaceLifecycleLink,
    WorkspaceReplayEvidence,
    WorkspaceResolvedContext,
    WorkspaceResumeRequest,
    WorkspaceSavedVersion,
    WorkspaceSavedVersionListResponse,
    WorkspaceSavedVersionSummary,
    WorkspaceSaveRequest,
    WorkspaceSaveResponse,
    WorkspaceSession,
    WorkspaceSessionCreateRequest,
    WorkspaceSessionCreateResponse,
    WorkspaceStatefulInput,
    WorkspaceStatelessInput,
    WorkspaceTradeDraft,
)
from src.integrations.lotus_core import (
    LotusCoreContextResolutionError,
    resolve_lotus_core_advisory_context,
)

MAX_WORKSPACE_SESSION_CACHE_SIZE = 500
WORKSPACE_SESSIONS: "OrderedDictType[str, WorkspaceSession]" = OrderedDict()


class WorkspaceNotFoundError(Exception):
    pass


class WorkspaceEvaluationUnavailableError(Exception):
    pass


class WorkspaceSavedVersionNotFoundError(Exception):
    pass


class WorkspaceLifecycleHandoffUnavailableError(Exception):
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
    try:
        return resolve_lotus_core_advisory_context(stateful_input).resolved_context
    except LotusCoreContextResolutionError:
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
    if session.input_mode == "stateful":
        if session.stateful_input is None:
            raise WorkspaceEvaluationUnavailableError("WORKSPACE_STATEFUL_INPUT_MISSING")
        try:
            resolved_stateful_context = resolve_lotus_core_advisory_context(session.stateful_input)
        except LotusCoreContextResolutionError as exc:
            raise WorkspaceEvaluationUnavailableError(
                "WORKSPACE_STATEFUL_CONTEXT_RESOLUTION_UNAVAILABLE"
            ) from exc
        session.resolved_context = resolved_stateful_context.resolved_context
        return resolved_stateful_context.simulate_request

    if session.stateless_input is None:
        raise WorkspaceEvaluationUnavailableError("WORKSPACE_STATELESS_INPUT_MISSING")

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
    suitability_issue_count = (
        len(result.suitability.issues) if result.suitability is not None else 0
    )
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


def _build_evaluation_summary(
    result: ProposalResult,
    session: WorkspaceSession,
) -> WorkspaceEvaluationSummary:
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


def _build_draft_state_hash(session: WorkspaceSession) -> str:
    return hash_canonical_payload(session.draft_state.model_dump(mode="json"))


def _build_replay_evidence(
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
        draft_state_hash=_build_draft_state_hash(session),
        evaluation_request_hash=evaluation_request_hash,
        captured_at=_utc_now_iso(),
    )


def _build_handoff_metadata(
    request: WorkspaceLifecycleHandoffRequest,
    session: WorkspaceSession,
) -> ProposalCreateMetadata:
    mandate_id = request.metadata.mandate_id
    if mandate_id is None and session.stateful_input is not None:
        mandate_id = session.stateful_input.mandate_id
    return ProposalCreateMetadata(
        title=request.metadata.title or session.workspace_name,
        advisor_notes=request.metadata.advisor_notes,
        jurisdiction=request.metadata.jurisdiction,
        mandate_id=mandate_id,
    )


def _build_saved_version_summary(
    version: WorkspaceSavedVersion,
) -> WorkspaceSavedVersionSummary:
    return WorkspaceSavedVersionSummary(
        workspace_version_id=version.workspace_version_id,
        version_number=version.version_number,
        version_label=version.version_label,
        saved_by=version.saved_by,
        saved_at=version.saved_at,
    )


def _refresh_saved_version_metadata(session: WorkspaceSession) -> None:
    session.saved_version_count = len(session.saved_versions)
    session.latest_saved_version = (
        _build_saved_version_summary(session.saved_versions[-1]) if session.saved_versions else None
    )


def _build_proposal_create_request(
    session: WorkspaceSession,
    request: WorkspaceLifecycleHandoffRequest,
) -> ProposalCreateRequest:
    return ProposalCreateRequest(
        created_by=request.handoff_by,
        simulate_request=_build_simulate_request_for_workspace(session),
        metadata=_build_handoff_metadata(request, session),
    )


def _build_proposal_version_request(
    session: WorkspaceSession,
    request: WorkspaceLifecycleHandoffRequest,
) -> ProposalVersionRequest:
    expected_current_version_no = (
        session.lifecycle_link.current_version_no if session.lifecycle_link is not None else None
    )
    return ProposalVersionRequest(
        created_by=request.handoff_by,
        expected_current_version_no=expected_current_version_no,
        simulate_request=_build_simulate_request_for_workspace(session),
    )


def reevaluate_workspace_session(workspace_id: str) -> WorkspaceSession:
    session = get_workspace_session(workspace_id)
    simulate_request = _build_simulate_request_for_workspace(session)
    request_payload = simulate_request.model_dump(mode="json")
    request_hash = hash_canonical_payload(request_payload)
    correlation_id = f"corr_{uuid4().hex[:12]}"
    result = evaluate_advisory_proposal(
        request=simulate_request,
        request_hash=request_hash,
        idempotency_key=None,
        correlation_id=correlation_id,
    )
    session.latest_proposal_result = result
    session.evaluation_summary = _build_evaluation_summary(result, session)
    session.latest_replay_evidence = _build_replay_evidence(
        session,
        evaluation_request_hash=request_hash,
    )
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


def _find_saved_version(
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
        raise WorkspaceSavedVersionNotFoundError("WORKSPACE_SAVED_VERSION_NOT_FOUND")
    return saved_version


def _find_trade_draft(
    session: WorkspaceSession,
    workspace_trade_id: str,
) -> WorkspaceTradeDraft:
    trade_draft = next(
        (
            item
            for item in session.draft_state.trade_drafts
            if item.workspace_trade_id == workspace_trade_id
        ),
        None,
    )
    if trade_draft is None:
        raise WorkspaceNotFoundError("WORKSPACE_TRADE_NOT_FOUND")
    return trade_draft


def _find_cash_flow_draft(
    session: WorkspaceSession, workspace_cash_flow_id: str
) -> WorkspaceCashFlowDraft:
    cash_flow_draft = next(
        (
            item
            for item in session.draft_state.cash_flow_drafts
            if item.workspace_cash_flow_id == workspace_cash_flow_id
        ),
        None,
    )
    if cash_flow_draft is None:
        raise WorkspaceNotFoundError("WORKSPACE_CASH_FLOW_NOT_FOUND")
    return cash_flow_draft


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
        latest_replay_evidence=None,
        saved_version_count=0,
        latest_saved_version=None,
        lifecycle_link=None,
        saved_versions=[],
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
        trade_draft = _find_trade_draft(session, request.workspace_trade_id)
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
        cash_flow_draft = _find_cash_flow_draft(session, request.workspace_cash_flow_id)
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


def save_workspace_version(
    workspace_id: str,
    request: WorkspaceSaveRequest,
) -> WorkspaceSaveResponse:
    session = get_workspace_session(workspace_id)
    replay_evidence = (
        session.latest_replay_evidence.model_copy(deep=True)
        if session.latest_replay_evidence is not None
        else _build_replay_evidence(session)
    )
    saved_version = WorkspaceSavedVersion(
        workspace_version_id=f"awv_{uuid4().hex[:12]}",
        version_number=len(session.saved_versions) + 1,
        version_label=request.version_label,
        saved_by=request.saved_by,
        saved_at=_utc_now_iso(),
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
    session.saved_versions.append(saved_version)
    _refresh_saved_version_metadata(session)
    _save_workspace_session(session)
    return WorkspaceSaveResponse(workspace=session, saved_version=saved_version)


def list_workspace_saved_versions(
    workspace_id: str,
) -> WorkspaceSavedVersionListResponse:
    session = get_workspace_session(workspace_id)
    return WorkspaceSavedVersionListResponse(
        workspace_id=session.workspace_id,
        saved_versions=[item.model_copy(deep=True) for item in session.saved_versions],
    )


def resume_workspace_version(
    workspace_id: str,
    request: WorkspaceResumeRequest,
) -> WorkspaceSession:
    session = get_workspace_session(workspace_id)
    saved_version = _find_saved_version(session, request.workspace_version_id)
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
    _save_workspace_session(session)
    return session


def compare_workspace_to_saved_version(
    workspace_id: str,
    request: WorkspaceCompareRequest,
) -> WorkspaceCompareResponse:
    session = get_workspace_session(workspace_id)
    saved_version = _find_saved_version(session, request.workspace_version_id)
    current_status = (
        session.evaluation_summary.status if session.evaluation_summary is not None else None
    )
    baseline_status = (
        saved_version.evaluation_summary.status
        if saved_version.evaluation_summary is not None
        else None
    )
    return WorkspaceCompareResponse(
        workspace_id=session.workspace_id,
        baseline_version=saved_version.model_copy(deep=True),
        current_evaluation_summary=(
            session.evaluation_summary.model_copy(deep=True)
            if session.evaluation_summary is not None
            else None
        ),
        current_replay_evidence=(
            session.latest_replay_evidence.model_copy(deep=True)
            if session.latest_replay_evidence is not None
            else None
        ),
        diff_summary=WorkspaceCompareDiffSummary(
            trade_count_delta=(
                len(session.draft_state.trade_drafts) - len(saved_version.draft_state.trade_drafts)
            ),
            cash_flow_count_delta=(
                len(session.draft_state.cash_flow_drafts)
                - len(saved_version.draft_state.cash_flow_drafts)
            ),
            options_changed=session.draft_state.options != saved_version.draft_state.options,
            reference_model_changed=(
                session.draft_state.reference_model != saved_version.draft_state.reference_model
            ),
            evaluation_status_changed=current_status != baseline_status,
        ),
    )


def handoff_workspace_to_proposal_lifecycle(
    workspace_id: str,
    request: WorkspaceLifecycleHandoffRequest,
    proposal_service: ProposalWorkflowService,
    idempotency_key: str | None,
    correlation_id: str | None,
) -> WorkspaceLifecycleHandoffResponse:
    session = get_workspace_session(workspace_id)
    try:
        if session.lifecycle_link is None:
            if not idempotency_key:
                raise WorkspaceLifecycleHandoffUnavailableError(
                    "WORKSPACE_HANDOFF_IDEMPOTENCY_KEY_REQUIRED"
                )
            proposal_response = proposal_service.create_proposal(
                payload=_build_proposal_create_request(session, request),
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                lifecycle_origin="WORKSPACE_HANDOFF",
                source_workspace_id=workspace_id,
            )
            handoff_action = "CREATED_PROPOSAL"
        else:
            proposal_response = proposal_service.create_version(
                proposal_id=session.lifecycle_link.proposal_id,
                payload=_build_proposal_version_request(session, request),
                correlation_id=correlation_id,
            )
            handoff_action = "CREATED_PROPOSAL_VERSION"
    except (ValueError, WorkspaceEvaluationUnavailableError) as exc:
        raise WorkspaceLifecycleHandoffUnavailableError(str(exc)) from exc

    session.lifecycle_link = WorkspaceLifecycleLink(
        proposal_id=proposal_response.proposal.proposal_id,
        current_version_no=proposal_response.version.version_no,
        last_handoff_at=_utc_now_iso(),
        last_handoff_by=request.handoff_by,
    )
    _save_workspace_session(session)
    return WorkspaceLifecycleHandoffResponse(
        workspace=session,
        handoff_action=handoff_action,
        proposal=proposal_response,
    )
