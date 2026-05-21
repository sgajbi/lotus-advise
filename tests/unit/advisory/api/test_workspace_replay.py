from src.api.services.workspace_service import (
    WorkspaceSessionCreateRequest,
    create_workspace_session,
    reset_workspace_sessions_for_tests,
)
from src.core.workspace.models import WorkspaceLifecycleHandoffRequest, WorkspaceSavedVersion
from src.core.workspace.replay import (
    apply_workspace_handoff_replay_lineage,
    build_replay_evidence,
    build_workspace_handoff_replay_lineage,
)


def setup_function() -> None:
    reset_workspace_sessions_for_tests()


def _session():
    return create_workspace_session(
        WorkspaceSessionCreateRequest.model_validate(
            {
                "workspace_name": "Replay workspace",
                "created_by": "advisor_123",
                "input_mode": "stateless",
                "stateless_input": {
                    "simulate_request": {
                        "portfolio_snapshot": {
                            "portfolio_id": "pf_replay",
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


def test_workspace_replay_lineage_links_latest_matching_saved_version():
    session = _session()
    session.latest_replay_evidence = build_replay_evidence(
        session,
        evaluation_request_hash="sha256:evaluation",
    )
    saved_version = WorkspaceSavedVersion(
        workspace_version_id="awv_saved",
        version_number=1,
        version_label="Baseline",
        saved_by="advisor_123",
        saved_at="2026-05-20T00:00:00+00:00",
        draft_state=session.draft_state.model_copy(deep=True),
        evaluation_summary=None,
        latest_proposal_result=None,
        replay_evidence=session.latest_replay_evidence.model_copy(deep=True),
    )
    session.saved_versions.append(saved_version)

    lineage = build_workspace_handoff_replay_lineage(
        session,
        WorkspaceLifecycleHandoffRequest(handoff_by="advisor_123"),
        "CREATED_PROPOSAL",
        proposal_id="pp_123456789abc",
        proposal_version_no=1,
    )
    apply_workspace_handoff_replay_lineage(session, lineage)

    assert lineage["workspace_id"] == session.workspace_id
    assert lineage["workspace_version_id"] == "awv_saved"
    assert lineage["evaluation_request_hash"] == "sha256:evaluation"
    assert session.latest_replay_evidence.continuity == lineage
    assert saved_version.replay_evidence.continuity == lineage
