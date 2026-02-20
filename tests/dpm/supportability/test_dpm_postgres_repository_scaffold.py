from src.infrastructure.dpm_runs.postgres import PostgresDpmRunRepository


def test_postgres_repository_requires_dsn():
    try:
        PostgresDpmRunRepository(dsn="")
    except RuntimeError as exc:
        assert str(exc) == "DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED"
    else:
        raise AssertionError("Expected RuntimeError for missing DSN")


def test_postgres_repository_requires_driver(monkeypatch):
    import src.infrastructure.dpm_runs.postgres as postgres_module

    monkeypatch.setattr(postgres_module, "find_spec", lambda _name: None)
    try:
        PostgresDpmRunRepository(dsn="postgresql://user:pass@localhost:5432/dpm")
    except RuntimeError as exc:
        assert str(exc) == "DPM_SUPPORTABILITY_POSTGRES_DRIVER_MISSING"
    else:
        raise AssertionError("Expected RuntimeError for missing psycopg driver")


def test_postgres_repository_reports_not_implemented_for_operations(monkeypatch):
    import src.infrastructure.dpm_runs.postgres as postgres_module

    monkeypatch.setattr(postgres_module, "find_spec", lambda _name: object())
    repository = PostgresDpmRunRepository(dsn="postgresql://user:pass@localhost:5432/dpm")
    assert repository._dsn == "postgresql://user:pass@localhost:5432/dpm"
    try:
        repository.save_run  # type: ignore[attr-defined]
    except RuntimeError as exc:
        assert str(exc) == "DPM_SUPPORTABILITY_POSTGRES_NOT_IMPLEMENTED"
    else:
        raise AssertionError("Expected RuntimeError for unimplemented method access")
