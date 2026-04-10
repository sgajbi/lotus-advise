from __future__ import annotations

import pytest

from scripts import run_runtime_smoke_checks


def test_postgres_env_honors_injected_ci_dsns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "PROPOSAL_POSTGRES_DSN", "postgresql://lotus:lotus@127.0.0.1:5432/lotus_advise"
    )
    monkeypatch.setenv(
        "PROPOSAL_POSTGRES_INTEGRATION_DSN",
        "postgresql://lotus:lotus@127.0.0.1:5432/lotus_advise_integration",
    )

    env = run_runtime_smoke_checks._postgres_env()

    assert env["PROPOSAL_POSTGRES_DSN"] == "postgresql://lotus:lotus@127.0.0.1:5432/lotus_advise"
    assert (
        env["PROPOSAL_POSTGRES_INTEGRATION_DSN"]
        == "postgresql://lotus:lotus@127.0.0.1:5432/lotus_advise_integration"
    )


def test_postgres_env_uses_integration_fallback_when_not_injected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)
    monkeypatch.delenv("PROPOSAL_POSTGRES_INTEGRATION_DSN", raising=False)

    env = run_runtime_smoke_checks._postgres_env()

    assert (
        env["PROPOSAL_POSTGRES_DSN"]
        == "postgresql://advise:advise@127.0.0.1:5432/advise_supportability"
    )
    assert env["PROPOSAL_POSTGRES_INTEGRATION_DSN"] == env["PROPOSAL_POSTGRES_DSN"]


def test_postgres_runtime_contracts_always_tears_down(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)
    monkeypatch.delenv("PROPOSAL_POSTGRES_INTEGRATION_DSN", raising=False)

    def fake_run_docker_compose(arguments: list[str]) -> None:
        events.append(" ".join(arguments))

    def fake_postgres_migration_smoke() -> None:
        events.append("postgres-migration-smoke")
        raise RuntimeError("smoke failed")

    monkeypatch.setattr(run_runtime_smoke_checks, "_run_docker_compose", fake_run_docker_compose)
    monkeypatch.setattr(
        run_runtime_smoke_checks,
        "_wait_for_postgres_ready",
        lambda dsn: events.append(dsn),
    )
    monkeypatch.setattr(
        run_runtime_smoke_checks, "run_postgres_migration_smoke", fake_postgres_migration_smoke
    )
    monkeypatch.setattr(
        run_runtime_smoke_checks,
        "run_production_profile_smoke",
        lambda: events.append("production-profile-smoke"),
    )

    with pytest.raises(RuntimeError, match="smoke failed"):
        run_runtime_smoke_checks.run_postgres_runtime_contracts()

    assert events == [
        "up -d --remove-orphans postgres",
        "postgresql://advise:advise@127.0.0.1:5432/advise_supportability",
        "postgres-migration-smoke",
        "down -v --remove-orphans",
    ]
