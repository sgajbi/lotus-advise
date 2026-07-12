import pytest

import src.api.production_cutover_contract as production_cutover_contract


def test_cutover_contract_validates_runtime_even_without_profile(monkeypatch):
    called: list[str] = []

    monkeypatch.setattr(
        production_cutover_contract,
        "validate_advisory_runtime_persistence",
        lambda: called.append("runtime"),
    )

    production_cutover_contract.validate_production_cutover_contract(check_migrations=False)

    assert called == ["runtime"]


def test_cutover_contract_checks_migrations_when_requested(monkeypatch):
    called: list[str] = []

    monkeypatch.setattr(
        production_cutover_contract,
        "validate_advisory_runtime_persistence",
        lambda: called.append("runtime"),
    )
    monkeypatch.setattr(
        production_cutover_contract,
        "validate_cutover_migrations_applied",
        lambda: called.append("migrations"),
    )

    production_cutover_contract.validate_production_cutover_contract(check_migrations=True)

    assert called == ["runtime", "migrations"]


def test_cutover_contract_includes_persistence_migration_namespaces():
    assert "proposals" in production_cutover_contract.CUTOVER_MIGRATION_NAMESPACES
    assert "advisory_copilot" in production_cutover_contract.CUTOVER_MIGRATION_NAMESPACES
    assert "policy_packs" in production_cutover_contract.CUTOVER_MIGRATION_NAMESPACES
    assert "workspace" in production_cutover_contract.CUTOVER_MIGRATION_NAMESPACES
    assert production_cutover_contract.expected_migration_versions(
        namespace="advisory_copilot"
    ) == ["0001", "0002", "0003"]
    assert production_cutover_contract.expected_migration_versions(namespace="policy_packs") == [
        "0001",
        "0002",
    ]
    assert production_cutover_contract.expected_migration_versions(namespace="workspace") == [
        "0001"
    ]


def test_cutover_contract_uses_policy_dsn_for_policy_namespace(monkeypatch):
    monkeypatch.setattr(
        production_cutover_contract,
        "proposal_postgres_dsn",
        lambda: "postgres://proposal",
    )
    monkeypatch.setattr(
        production_cutover_contract,
        "policy_postgres_dsn",
        lambda: "postgres://policy",
    )

    assert (
        production_cutover_contract.cutover_namespace_dsn(namespace="policy_packs")
        == "postgres://policy"
    )
    assert (
        production_cutover_contract.cutover_namespace_dsn(namespace="proposals")
        == "postgres://proposal"
    )


def test_cutover_contract_uses_workspace_dsn_or_proposal_fallback(monkeypatch):
    monkeypatch.setattr(
        production_cutover_contract,
        "proposal_postgres_dsn",
        lambda: "postgres://proposal",
    )
    monkeypatch.delenv("WORKSPACE_POSTGRES_DSN", raising=False)

    assert (
        production_cutover_contract.cutover_namespace_dsn(namespace="workspace")
        == "postgres://proposal"
    )

    monkeypatch.setenv("WORKSPACE_POSTGRES_DSN", "postgres://workspace")

    assert (
        production_cutover_contract.cutover_namespace_dsn(namespace="workspace")
        == "postgres://workspace"
    )


def test_cutover_contract_propagates_runtime_failures(monkeypatch):
    def _raise_runtime_failure():
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN")

    monkeypatch.setattr(
        production_cutover_contract,
        "validate_advisory_runtime_persistence",
        _raise_runtime_failure,
    )

    with pytest.raises(RuntimeError) as exc:
        production_cutover_contract.validate_production_cutover_contract(check_migrations=False)

    assert str(exc.value) == "PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN"
