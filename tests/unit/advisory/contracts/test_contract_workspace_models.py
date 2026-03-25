from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.core.models import (
    GateDecision,
    GateDecisionSummary,
    GateReason,
    MarketDataSnapshot,
    Money,
    PortfolioSnapshot,
    ProposalResult,
    ProposalSimulateRequest,
    Reconciliation,
    RuleResult,
    ShelfEntry,
    SimulatedState,
)
from src.core.workspace.models import (
    WorkspaceCompareRequest,
    WorkspaceCompareResponse,
    WorkspaceDraftActionRequest,
    WorkspaceDraftState,
    WorkspaceEvaluationImpactSummary,
    WorkspaceEvaluationSummary,
    WorkspaceReplayEvidence,
    WorkspaceResolvedContext,
    WorkspaceSavedVersion,
    WorkspaceSavedVersionSummary,
    WorkspaceSaveRequest,
    WorkspaceSession,
    WorkspaceSessionCreateRequest,
    WorkspaceStatefulInput,
    WorkspaceStatelessInput,
)


def _build_state() -> SimulatedState:
    return SimulatedState(
        total_value=Money(amount=Decimal("1000"), currency="USD"),
        cash_balances=[],
        positions=[],
        allocation_by_asset_class=[],
        allocation_by_instrument=[],
        allocation=[],
        allocation_by_attribute={},
    )


def _build_proposal_result() -> ProposalResult:
    state = _build_state()
    return ProposalResult(
        proposal_run_id="pr_workspace",
        correlation_id="corr_workspace",
        status="READY",
        before=state,
        intents=[],
        after_simulated=state,
        reconciliation=Reconciliation(
            before_total_value=Money(amount=Decimal("1000"), currency="USD"),
            after_total_value=Money(amount=Decimal("1000"), currency="USD"),
            delta=Money(amount=Decimal("0"), currency="USD"),
            tolerance=Money(amount=Decimal("1"), currency="USD"),
            status="OK",
        ),
        rule_results=[
            RuleResult(
                rule_id="DATA_QUALITY",
                severity="HARD",
                status="PASS",
                measured=Decimal("0"),
                threshold={"max": Decimal("0")},
                reason_code="OK",
            )
        ],
        explanation={"summary": "READY"},
        diagnostics={"data_quality": {"price_missing": [], "fx_missing": [], "shelf_missing": []}},
        lineage={
            "portfolio_snapshot_id": "ps_001",
            "market_data_snapshot_id": "md_001",
            "request_hash": "sha256:test",
        },
    )


def test_workspace_create_request_requires_stateless_input_for_stateless_mode():
    simulate_request = ProposalSimulateRequest(
        portfolio_snapshot=PortfolioSnapshot(portfolio_id="pf_1", base_currency="USD"),
        market_data_snapshot=MarketDataSnapshot(prices=[], fx_rates=[]),
        shelf_entries=[ShelfEntry(instrument_id="EQ_1", status="APPROVED")],
        options={"enable_proposal_simulation": True},
        proposed_cash_flows=[],
        proposed_trades=[],
    )

    request = WorkspaceSessionCreateRequest(
        workspace_name="Sandbox proposal",
        created_by="advisor_123",
        input_mode="stateless",
        stateless_input=WorkspaceStatelessInput(simulate_request=simulate_request),
    )

    assert request.input_mode == "stateless"
    assert request.stateless_input is not None
    assert request.stateful_input is None


def test_workspace_create_request_rejects_mixed_mode_payloads():
    with pytest.raises(ValidationError):
        WorkspaceSessionCreateRequest(
            workspace_name="Bad mixed workspace",
            created_by="advisor_123",
            input_mode="stateful",
            stateless_input=WorkspaceStatelessInput(
                simulate_request=ProposalSimulateRequest(
                    portfolio_snapshot=PortfolioSnapshot(portfolio_id="pf_1", base_currency="USD"),
                    market_data_snapshot=MarketDataSnapshot(prices=[], fx_rates=[]),
                    shelf_entries=[],
                    options={"enable_proposal_simulation": True},
                    proposed_cash_flows=[],
                    proposed_trades=[],
                )
            ),
            stateful_input=WorkspaceStatefulInput(portfolio_id="pf_1", as_of="2026-03-25"),
        )


def test_workspace_session_supports_stateful_context_and_evaluation_summary():
    session = WorkspaceSession(
        workspace_id="aws_001",
        workspace_name="Q2 2026 growth reallocation draft",
        lifecycle_state="ACTIVE",
        input_mode="stateful",
        created_by="advisor_123",
        created_at="2026-03-25T09:30:00+00:00",
        stateful_input=WorkspaceStatefulInput(
            portfolio_id="pf_advisory_01",
            household_id="hh_001",
            as_of="2026-03-25",
            mandate_id="mandate_growth_01",
        ),
        draft_state=WorkspaceDraftState(),
        resolved_context=WorkspaceResolvedContext(
            portfolio_id="pf_advisory_01",
            as_of="2026-03-25",
            portfolio_snapshot_id="ps_001",
            market_data_snapshot_id="md_001",
            risk_context_id="risk_001",
        ),
            evaluation_summary=WorkspaceEvaluationSummary(
                status="PENDING_REVIEW",
                gate_decision=GateDecision(
                    gate="RISK_REVIEW_REQUIRED",
                    recommended_next_step="RISK_REVIEW",
                    reasons=[
                        GateReason(
                            reason_code="ISSUER_CONCENTRATION",
                            severity="HIGH",
                            source="SUITABILITY",
                        details={"message": "Issuer concentration exceeds advisory threshold."},
                    )
                ],
                summary=GateDecisionSummary(
                    hard_fail_count=0,
                    soft_fail_count=1,
                    new_high_suitability_count=1,
                    new_medium_suitability_count=0,
                ),
            ),
            blocking_issue_count=0,
            review_issue_count=1,
            impact_summary=WorkspaceEvaluationImpactSummary(
                portfolio_value_delta_base_ccy="-1250.50",
                trade_count=3,
                cash_flow_count=1,
            ),
        ),
        latest_proposal_result=_build_proposal_result(),
    )

    assert session.input_mode == "stateful"
    assert session.resolved_context is not None
    assert session.evaluation_summary is not None
    assert session.evaluation_summary.review_issue_count == 1


def test_workspace_schema_exposes_examples_and_descriptions():
    schema = WorkspaceSessionCreateRequest.model_json_schema()
    properties = schema["properties"]

    assert properties["workspace_name"]["description"]
    assert properties["input_mode"]["examples"] == ["stateful"]
    assert "examples" in properties["stateless_input"]


def test_workspace_draft_action_requires_trade_for_add_trade():
    with pytest.raises(ValidationError):
        WorkspaceDraftActionRequest(actor_id="advisor_123", action_type="ADD_TRADE")


def test_workspace_draft_action_supports_update_trade_payload():
    action = WorkspaceDraftActionRequest(
        actor_id="advisor_123",
        action_type="UPDATE_TRADE",
        workspace_trade_id="wtd_001",
        trade={"side": "BUY", "instrument_id": "EQ_1", "quantity": "2"},
    )

    assert action.workspace_trade_id == "wtd_001"
    assert action.trade is not None


def test_workspace_save_and_compare_models_capture_replay_safe_history():
    replay_evidence = WorkspaceReplayEvidence(
        input_mode="stateless",
        resolved_context=WorkspaceResolvedContext(portfolio_id="pf_advisory_01", as_of="2026-03-25"),
        draft_state_hash="hash_001",
        evaluation_request_hash="eval_hash_001",
        captured_at="2026-03-25T09:45:00+00:00",
    )
    saved_version = WorkspaceSavedVersion(
        workspace_version_id="awv_001",
        version_number=1,
        version_label="Initial sandbox draft",
        saved_by="advisor_123",
        saved_at="2026-03-25T09:45:00+00:00",
        draft_state=WorkspaceDraftState(),
        evaluation_summary=None,
        latest_proposal_result=None,
        replay_evidence=replay_evidence,
    )
    save_request = WorkspaceSaveRequest(saved_by="advisor_123", version_label="Initial sandbox draft")
    compare_request = WorkspaceCompareRequest(workspace_version_id="awv_001")
    summary = WorkspaceSavedVersionSummary(
        workspace_version_id="awv_001",
        version_number=1,
        version_label="Initial sandbox draft",
        saved_by="advisor_123",
        saved_at="2026-03-25T09:45:00+00:00",
    )

    assert save_request.saved_by == "advisor_123"
    assert compare_request.workspace_version_id == "awv_001"
    assert saved_version.replay_evidence.evaluation_request_hash == "eval_hash_001"
    assert summary.version_number == 1


def test_workspace_compare_response_schema_is_instantiable():
    response = WorkspaceCompareResponse(
        workspace_id="aws_001",
        baseline_version=WorkspaceSavedVersion(
            workspace_version_id="awv_001",
            version_number=1,
            version_label="Initial sandbox draft",
            saved_by="advisor_123",
            saved_at="2026-03-25T09:45:00+00:00",
            draft_state=WorkspaceDraftState(),
            evaluation_summary=None,
            latest_proposal_result=None,
            replay_evidence=WorkspaceReplayEvidence(
                input_mode="stateless",
                resolved_context=None,
                draft_state_hash="hash_001",
                evaluation_request_hash=None,
                captured_at="2026-03-25T09:45:00+00:00",
            ),
        ),
        current_evaluation_summary=None,
        current_replay_evidence=None,
        diff_summary={
            "trade_count_delta": 1,
            "cash_flow_count_delta": 0,
            "options_changed": False,
            "reference_model_changed": False,
            "evaluation_status_changed": False,
        },
    )

    assert response.diff_summary.trade_count_delta == 1
