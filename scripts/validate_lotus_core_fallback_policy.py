from __future__ import annotations

import sys
from contextlib import ExitStack
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FallbackPolicyValidationError(RuntimeError):
    pass


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise FallbackPolicyValidationError(message)


def validate_lotus_core_fallback_policy() -> None:
    from fastapi.testclient import TestClient
    from pytest import MonkeyPatch

    from src.infrastructure.proposals.in_memory import InMemoryProposalRepository
    from src.integrations.lotus_core.stateful_context import (
        reset_stateful_context_cache_for_tests,
    )

    monkeypatch = MonkeyPatch()
    with ExitStack() as stack:
        stack.callback(monkeypatch.undo)
        monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
        monkeypatch.setenv(
            "PROPOSAL_POSTGRES_DSN",
            "postgresql://test:test@localhost:5432/proposals",
        )
        monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://core-control.dev.lotus")
        monkeypatch.setenv("LOTUS_ADVISE_ALLOW_LOCAL_SIMULATION_FALLBACK", "true")
        monkeypatch.setenv("LOTUS_RISK_BASE_URL", "")
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setattr(
            "src.api.proposals.runtime.PostgresProposalRepository",
            lambda **_kwargs: InMemoryProposalRepository(),
        )
        import src.core.advisory.orchestration as orchestration
        from src.api.main import app
        from src.api.proposals.router import reset_proposal_workflow_service_for_tests
        from src.integrations.lotus_core.simulation import LotusCoreSimulationUnavailableError

        monkeypatch.setattr(
            orchestration,
            "simulate_with_lotus_core",
            lambda **kwargs: (_ for _ in ()).throw(
                LotusCoreSimulationUnavailableError("LOTUS_CORE_SIMULATION_UNAVAILABLE")
            ),
        )

        reset_proposal_workflow_service_for_tests()
        reset_stateful_context_cache_for_tests()

        with TestClient(app) as client:
            stateless = client.post(
                "/advisory/proposals/simulate",
                json={
                    "portfolio_snapshot": {
                        "portfolio_id": "pf_stateless_fallback",
                        "base_currency": "USD",
                    },
                    "market_data_snapshot": {"prices": [], "fx_rates": []},
                    "shelf_entries": [],
                    "options": {"enable_proposal_simulation": True},
                    "proposed_cash_flows": [],
                    "proposed_trades": [],
                },
                headers={"Idempotency-Key": "fallback-policy-stateless"},
            )
            _assert(stateless.status_code == 200, f"stateless simulate failed: {stateless.text}")
            authority = stateless.json()["explanation"]["authority_resolution"]
            _assert(
                authority["simulation_authority"] == "lotus_advise_local_fallback",
                f"unexpected stateless authority {authority}",
            )

            stateful_create = client.post(
                "/advisory/proposals",
                json={
                    "created_by": "advisor_1",
                    "input_mode": "stateful",
                    "stateful_input": {
                        "portfolio_id": "pf_missing_stateful_create",
                        "as_of": "2026-03-25",
                    },
                },
                headers={"Idempotency-Key": "fallback-policy-stateful-create"},
            )
            _assert(
                stateful_create.status_code == 422,
                f"stateful create unexpectedly succeeded: {stateful_create.text}",
            )
            _assert(
                stateful_create.json()["detail"]
                == "PROPOSAL_STATEFUL_CONTEXT_RESOLUTION_UNAVAILABLE",
                f"unexpected stateful create detail {stateful_create.text}",
            )

            workspace = client.post(
                "/advisory/workspaces",
                json={
                    "workspace_name": "Fallback policy validator",
                    "created_by": "advisor_1",
                    "input_mode": "stateful",
                    "stateful_input": {
                        "portfolio_id": "pf_missing_stateful_workspace",
                        "as_of": "2026-03-25",
                    },
                },
            )
            _assert(workspace.status_code == 201, f"workspace create failed: {workspace.text}")
            workspace_id = workspace.json()["workspace"]["workspace_id"]
            evaluated = client.post(f"/advisory/workspaces/{workspace_id}/evaluate")
            _assert(
                evaluated.status_code == 409,
                f"stateful workspace unexpectedly succeeded: {evaluated.text}",
            )
            _assert(
                evaluated.json()["detail"] == "WORKSPACE_STATEFUL_CONTEXT_RESOLUTION_UNAVAILABLE",
                f"unexpected stateful workspace detail {evaluated.text}",
            )

            monkeypatch.setenv("ENVIRONMENT", "production")
            production_stateless = client.post(
                "/advisory/proposals/simulate",
                json={
                    "portfolio_snapshot": {
                        "portfolio_id": "pf_prod_guard",
                        "base_currency": "USD",
                    },
                    "market_data_snapshot": {"prices": [], "fx_rates": []},
                    "shelf_entries": [],
                    "options": {"enable_proposal_simulation": True},
                    "proposed_cash_flows": [],
                    "proposed_trades": [],
                },
                headers={"Idempotency-Key": "fallback-policy-production"},
            )
            _assert(
                production_stateless.status_code == 503,
                f"production fallback unexpectedly succeeded: {production_stateless.text}",
            )
            _assert(
                production_stateless.json()["detail"]
                == "LOTUS_CORE_SIMULATION_REQUIRED_IN_THIS_ENVIRONMENT",
                f"unexpected production fallback detail {production_stateless.text}",
            )


def main() -> None:
    validate_lotus_core_fallback_policy()
    print("Lotus Core fallback policy validation passed")


if __name__ == "__main__":
    main()
