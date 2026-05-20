import pytest

from src.api.services.workspace_service import (
    WorkspaceSessionCreateRequest,
    create_workspace_session,
    reset_workspace_sessions_for_tests,
)
from src.core.workspace.handoff import (
    WorkspaceHandoffError,
    build_handoff_metadata,
    build_proposal_create_request,
    build_workspace_handoff_context_resolution,
)
from src.core.workspace.models import WorkspaceLifecycleHandoffRequest


def setup_function() -> None:
    reset_workspace_sessions_for_tests()


def _session():
    return create_workspace_session(
        WorkspaceSessionCreateRequest.model_validate(
            {
                "workspace_name": "Handoff workspace",
                "created_by": "advisor_123",
                "input_mode": "stateless",
                "stateless_input": {
                    "simulate_request": {
                        "portfolio_snapshot": {
                            "portfolio_id": "pf_handoff",
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


def test_build_handoff_metadata_uses_request_title_and_workspace_fallback():
    session = _session()
    default_metadata = build_handoff_metadata(
        WorkspaceLifecycleHandoffRequest(handoff_by="advisor_123"),
        session,
    )
    titled_metadata = build_handoff_metadata(
        WorkspaceLifecycleHandoffRequest(
            handoff_by="advisor_123",
            metadata={"title": "Client proposal"},
        ),
        session,
    )

    assert default_metadata.title == "Handoff workspace"
    assert titled_metadata.title == "Client proposal"


def test_build_proposal_create_request_and_context_resolution_use_workspace_context():
    session = _session()
    assert session.stateless_input is not None
    create_request = build_proposal_create_request(
        session,
        WorkspaceLifecycleHandoffRequest(handoff_by="advisor_123"),
        session.stateless_input.simulate_request,
    )
    context_resolution = build_workspace_handoff_context_resolution(
        session,
        create_request.simulate_request,
        create_request.metadata,
    )

    assert create_request.created_by == "advisor_123"
    assert context_resolution["resolution_source"] == "DIRECT_REQUEST"
    assert context_resolution["resolved_context"]["portfolio_id"] == "pf_handoff"


def test_build_workspace_handoff_context_resolution_requires_resolved_context():
    session = _session()
    assert session.stateless_input is not None
    session.resolved_context = None

    with pytest.raises(WorkspaceHandoffError) as exc:
        build_workspace_handoff_context_resolution(
            session,
            session.stateless_input.simulate_request,
            build_handoff_metadata(
                WorkspaceLifecycleHandoffRequest(handoff_by="advisor_123"), session
            ),
        )

    assert str(exc.value) == "WORKSPACE_RESOLVED_CONTEXT_MISSING"
