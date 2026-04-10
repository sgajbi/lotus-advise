from __future__ import annotations

import pytest

from scripts import run_runtime_smoke_checks


def test_postgres_runtime_contracts_always_tears_down(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

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
