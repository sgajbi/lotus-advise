import pytest

from src.core.models import ProposalSimulateRequest
from src.core.workspace.models import (
    WorkspaceResolvedContext,
    WorkspaceSession,
    WorkspaceStatefulInput,
)
from src.core.workspace.reevaluation import (
    WorkspaceReevaluationContextError,
    build_workspace_evaluation_context,
)


def _simulate_request() -> ProposalSimulateRequest:
    return ProposalSimulateRequest.model_validate(
        {
            "portfolio_snapshot": {
                "portfolio_id": "pf_reeval",
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
    )


def test_build_workspace_evaluation_context_uses_stateful_policy_selectors() -> None:
    session = WorkspaceSession.model_construct(
        input_mode="stateful",
        stateful_input=WorkspaceStatefulInput(
            portfolio_id="pf_reeval",
            as_of="2026-05-20",
            household_id="hh_001",
            mandate_id="mandate_growth_01",
            benchmark_id="benchmark_balanced",
        ),
        resolved_context=WorkspaceResolvedContext(
            portfolio_id="pf_reeval",
            as_of="2026-05-20",
            portfolio_snapshot_id="ps_reeval",
            market_data_snapshot_id="md_reeval",
        ),
    )

    evaluation_context = build_workspace_evaluation_context(
        session=session,
        simulate_request=_simulate_request(),
    )

    assert evaluation_context.resolved_request.resolution_source == "LOTUS_CORE"
    assert evaluation_context.resolved_request.resolved_context.as_of == "2026-05-20"
    assert evaluation_context.resolved_request.policy_selectors.household_id == "hh_001"
    assert evaluation_context.resolved_request.policy_selectors.mandate_id == "mandate_growth_01"
    assert evaluation_context.resolved_request.policy_selectors.benchmark_id == "benchmark_balanced"
    assert evaluation_context.context_resolution["resolution_source"] == "LOTUS_CORE"
    assert evaluation_context.request_hash.startswith("sha256:")
    assert len(evaluation_context.request_hash) == 71


def test_build_workspace_evaluation_context_requires_resolved_context() -> None:
    session = WorkspaceSession.model_construct(
        input_mode="stateless",
        stateful_input=None,
        resolved_context=None,
    )

    with pytest.raises(
        WorkspaceReevaluationContextError,
        match="WORKSPACE_RESOLVED_CONTEXT_MISSING",
    ):
        build_workspace_evaluation_context(
            session=session,
            simulate_request=_simulate_request(),
        )
