import pytest

from src.api.services.workspace_service import (
    WorkspaceSessionCreateRequest,
    create_workspace_session,
    reset_workspace_sessions_for_tests,
)
from src.core.workspace.models import WorkspaceSavedVersion
from src.core.workspace.replay import build_replay_evidence
from src.core.workspace.versions import (
    WorkspaceSavedVersionLookupError,
    find_saved_version,
    refresh_saved_version_metadata,
)


def setup_function() -> None:
    reset_workspace_sessions_for_tests()


def _session():
    return create_workspace_session(
        WorkspaceSessionCreateRequest.model_validate(
            {
                "workspace_name": "Version workspace",
                "created_by": "advisor_123",
                "input_mode": "stateless",
                "stateless_input": {
                    "simulate_request": {
                        "portfolio_snapshot": {
                            "portfolio_id": "pf_versions",
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


def _saved_version(session, *, workspace_version_id: str = "awv_saved"):
    return WorkspaceSavedVersion(
        workspace_version_id=workspace_version_id,
        version_number=1,
        version_label="Baseline",
        saved_by="advisor_123",
        saved_at="2026-05-20T00:00:00+00:00",
        draft_state=session.draft_state.model_copy(deep=True),
        evaluation_summary=None,
        latest_proposal_result=None,
        replay_evidence=build_replay_evidence(session),
    )


def test_refresh_saved_version_metadata_tracks_latest_version_summary():
    session = _session()
    first = _saved_version(session, workspace_version_id="awv_first")
    second = _saved_version(session, workspace_version_id="awv_second")
    second.version_number = 2
    session.saved_versions.extend([first, second])

    refresh_saved_version_metadata(session)

    assert session.saved_version_count == 2
    assert session.latest_saved_version is not None
    assert session.latest_saved_version.workspace_version_id == "awv_second"
    assert session.latest_saved_version.version_number == 2


def test_find_saved_version_returns_match_and_rejects_missing_id():
    session = _session()
    saved = _saved_version(session)
    session.saved_versions.append(saved)

    assert find_saved_version(session, "awv_saved") is saved
    with pytest.raises(WorkspaceSavedVersionLookupError) as exc:
        find_saved_version(session, "awv_missing")

    assert str(exc.value) == "WORKSPACE_SAVED_VERSION_NOT_FOUND"
