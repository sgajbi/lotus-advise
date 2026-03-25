from decimal import Decimal

import pytest

from src.api.services import workspace_service
from src.api.services.workspace_service import (
    WorkspaceDraftActionRequest,
    WorkspaceEvaluationUnavailableError,
    WorkspaceSessionCreateRequest,
    create_workspace_session,
    get_workspace_session,
    handoff_workspace_to_proposal_lifecycle,
    reset_workspace_sessions_for_tests,
)


def setup_function() -> None:
    reset_workspace_sessions_for_tests()


def test_workspace_session_cache_evicts_oldest_entry() -> None:
    original_limit = workspace_service.MAX_WORKSPACE_SESSION_CACHE_SIZE
    workspace_service.MAX_WORKSPACE_SESSION_CACHE_SIZE = 1
    try:
        first = create_workspace_session(
            WorkspaceSessionCreateRequest.model_validate(
                {
                    "workspace_name": "First workspace",
                    "created_by": "advisor_123",
                    "input_mode": "stateful",
                    "stateful_input": {"portfolio_id": "pf_001", "as_of": "2026-03-25"},
                }
            )
        ).workspace
        second = create_workspace_session(
            WorkspaceSessionCreateRequest.model_validate(
                {
                    "workspace_name": "Second workspace",
                    "created_by": "advisor_123",
                    "input_mode": "stateful",
                    "stateful_input": {"portfolio_id": "pf_002", "as_of": "2026-03-25"},
                }
            )
        ).workspace

        with pytest.raises(workspace_service.WorkspaceNotFoundError):
            get_workspace_session(first.workspace_id)

        assert get_workspace_session(second.workspace_id).workspace_name == "Second workspace"
    finally:
        workspace_service.MAX_WORKSPACE_SESSION_CACHE_SIZE = original_limit
        reset_workspace_sessions_for_tests()


def test_create_workspace_session_rejects_malformed_constructed_requests() -> None:
    malformed_stateless = WorkspaceSessionCreateRequest.model_construct(
        workspace_name="Bad stateless",
        created_by="advisor_123",
        input_mode="stateless",
        stateless_input=None,
        stateful_input=None,
    )
    malformed_stateful = WorkspaceSessionCreateRequest.model_construct(
        workspace_name="Bad stateful",
        created_by="advisor_123",
        input_mode="stateful",
        stateless_input=None,
        stateful_input=None,
    )

    with pytest.raises(ValueError, match="stateless workspace creation requires stateless_input"):
        create_workspace_session(malformed_stateless)

    with pytest.raises(ValueError, match="stateful workspace creation requires stateful_input"):
        create_workspace_session(malformed_stateful)


def test_workspace_service_replace_options_and_stateful_handoff_guard() -> None:
    session = create_workspace_session(
        WorkspaceSessionCreateRequest.model_validate(
            {
                "workspace_name": "Stateful workspace",
                "created_by": "advisor_123",
                "input_mode": "stateful",
                "stateful_input": {
                    "portfolio_id": "pf_001",
                    "household_id": "hh_001",
                    "mandate_id": "mandate_growth_01",
                    "as_of": "2026-03-25",
                },
            }
        )
    ).workspace

    with pytest.raises(
        WorkspaceEvaluationUnavailableError,
        match="WORKSPACE_STATEFUL_EVALUATION_NOT_IMPLEMENTED",
    ):
        workspace_service._build_simulate_request_for_workspace(session)

    request = WorkspaceDraftActionRequest.model_validate(
        {
            "actor_id": "advisor_123",
            "action_type": "REPLACE_OPTIONS",
            "options": {
                "enable_proposal_simulation": True,
                "auto_funding": False,
                "fx_buffer_pct": Decimal("0.02"),
            },
        }
    )
    session.draft_state.options = request.options.model_copy(deep=True)
    assert session.draft_state.options.auto_funding is False
    assert session.draft_state.options.fx_buffer_pct == Decimal("0.02")

    class FakeProposalService:
        def create_proposal(self, *args, **kwargs):  # pragma: no cover - should not be reached
            raise AssertionError("create_proposal should not be called for stateful handoff guard")

        def create_version(self, *args, **kwargs):  # pragma: no cover - should not be reached
            raise AssertionError("create_version should not be called for stateful handoff guard")

    with pytest.raises(
        workspace_service.WorkspaceLifecycleHandoffUnavailableError,
        match="WORKSPACE_STATEFUL_EVALUATION_NOT_IMPLEMENTED",
    ):
        handoff_workspace_to_proposal_lifecycle(
            workspace_id=session.workspace_id,
            request=workspace_service.WorkspaceLifecycleHandoffRequest(
                handoff_by="advisor_123"
            ),
            proposal_service=FakeProposalService(),
            idempotency_key="workspace-handoff-idem-direct",
            correlation_id=None,
        )


def test_workspace_service_trade_and_cash_flow_not_found_guards() -> None:
    session = create_workspace_session(
        WorkspaceSessionCreateRequest.model_validate(
            {
                "workspace_name": "Sandbox workspace",
                "created_by": "advisor_123",
                "input_mode": "stateless",
                "stateless_input": {
                    "simulate_request": {
                        "portfolio_snapshot": {
                            "portfolio_id": "pf_001",
                            "base_currency": "USD",
                            "positions": [],
                            "cash_balances": [{"currency": "USD", "amount": "1000"}],
                        },
                        "market_data_snapshot": {"prices": [], "fx_rates": []},
                        "shelf_entries": [],
                        "options": {"enable_proposal_simulation": True},
                        "proposed_cash_flows": [],
                        "proposed_trades": [],
                    }
                },
            }
        )
    ).workspace

    with pytest.raises(
        workspace_service.WorkspaceNotFoundError,
        match="WORKSPACE_CASH_FLOW_NOT_FOUND",
    ):
        workspace_service._find_cash_flow_draft(session, "wcf_missing")

    with pytest.raises(workspace_service.WorkspaceNotFoundError, match="WORKSPACE_TRADE_NOT_FOUND"):
        workspace_service.apply_workspace_draft_action(
            session.workspace_id,
            WorkspaceDraftActionRequest.model_validate(
                {
                    "actor_id": "advisor_123",
                    "action_type": "REMOVE_TRADE",
                    "workspace_trade_id": "wtd_missing",
                }
            ),
        )


def test_workspace_service_portfolio_delta_and_mandate_fallback() -> None:
    summary_request = WorkspaceSessionCreateRequest.model_validate(
        {
            "workspace_name": "Sandbox workspace",
            "created_by": "advisor_123",
            "input_mode": "stateful",
            "stateful_input": {
                "portfolio_id": "pf_001",
                "mandate_id": "mandate_growth_01",
                "as_of": "2026-03-25",
            },
        }
    )
    session = create_workspace_session(summary_request).workspace

    metadata = workspace_service._build_handoff_metadata(
        workspace_service.WorkspaceLifecycleHandoffRequest(handoff_by="advisor_123"),
        session,
    )
    assert metadata.mandate_id == "mandate_growth_01"

    class ResultWithoutReconciliation:
        reconciliation = None

        class after_simulated:
            total_value = type("MoneyHolder", (), {"amount": Decimal("120.00")})()

        class before:
            total_value = type("MoneyHolder", (), {"amount": Decimal("100.00")})()

    assert workspace_service._format_portfolio_delta(ResultWithoutReconciliation()) == "20.00"
