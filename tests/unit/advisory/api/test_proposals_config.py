import builtins

import pytest

from src.api.routers import proposals_config


def test_proposal_backend_alias_and_default(monkeypatch):
    monkeypatch.delenv("PROPOSAL_STORE_BACKEND", raising=False)
    with pytest.warns(DeprecationWarning):
        assert proposals_config.proposal_store_backend_name() == "IN_MEMORY"

    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    assert proposals_config.proposal_store_backend_name() == "POSTGRES"

    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "unknown")
    with pytest.warns(DeprecationWarning):
        assert proposals_config.proposal_store_backend_name() == "IN_MEMORY"


def test_proposal_postgres_dsn(monkeypatch):
    monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)
    assert proposals_config.proposal_postgres_dsn() == ""

    monkeypatch.setenv(
        "PROPOSAL_POSTGRES_DSN",
        "postgresql://user:pass@localhost:5432/proposals",
    )
    assert (
        proposals_config.proposal_postgres_dsn()
        == "postgresql://user:pass@localhost:5432/proposals"
    )


def test_build_repository_postgres_requires_dsn(monkeypatch):
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)

    try:
        proposals_config.build_repository()
    except RuntimeError as exc:
        assert str(exc) == "PROPOSAL_POSTGRES_DSN_REQUIRED"
    else:
        raise AssertionError("Expected RuntimeError for missing proposal postgres dsn")


def test_build_repository_postgres_not_implemented(monkeypatch):
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv(
        "PROPOSAL_POSTGRES_DSN",
        "postgresql://user:pass@localhost:5432/proposals",
    )

    def _raise_not_implemented(**_kwargs):
        raise RuntimeError("PROPOSAL_POSTGRES_NOT_IMPLEMENTED")

    monkeypatch.setattr(
        proposals_config,
        "PostgresProposalRepository",
        _raise_not_implemented,
    )
    try:
        proposals_config.build_repository()
    except RuntimeError as exc:
        assert str(exc) == "PROPOSAL_POSTGRES_NOT_IMPLEMENTED"
    else:
        raise AssertionError("Expected RuntimeError for unimplemented proposal postgres backend")


def test_build_repository_postgres_driver_error_passthrough(monkeypatch):
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv(
        "PROPOSAL_POSTGRES_DSN",
        "postgresql://user:pass@localhost:5432/proposals",
    )

    def _raise_driver_error(**_kwargs):
        raise RuntimeError("PROPOSAL_POSTGRES_DRIVER_MISSING")

    monkeypatch.setattr(
        proposals_config,
        "PostgresProposalRepository",
        _raise_driver_error,
    )
    try:
        proposals_config.build_repository()
    except RuntimeError as exc:
        assert str(exc) == "PROPOSAL_POSTGRES_DRIVER_MISSING"
    else:
        raise AssertionError("Expected RuntimeError passthrough for proposal postgres driver error")


def test_build_repository_postgres_connection_failure_mapped(monkeypatch):
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv(
        "PROPOSAL_POSTGRES_DSN",
        "postgresql://user:pass@localhost:5432/proposals",
    )

    def _raise_connection_error(**_kwargs):
        raise ValueError("connection failure")

    monkeypatch.setattr(
        proposals_config,
        "PostgresProposalRepository",
        _raise_connection_error,
    )
    try:
        proposals_config.build_repository()
    except RuntimeError as exc:
        assert str(exc) == "PROPOSAL_POSTGRES_CONNECTION_FAILED"
    else:
        raise AssertionError("Expected RuntimeError for proposal postgres connection failure")


def test_postgres_connection_exception_types_handles_missing_driver(monkeypatch):
    original_import = builtins.__import__

    def _import_with_psycopg_missing(name, *args, **kwargs):
        if name == "psycopg":
            raise ImportError("psycopg not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import_with_psycopg_missing)
    exception_types = proposals_config._postgres_connection_exception_types()
    assert ValueError in exception_types
