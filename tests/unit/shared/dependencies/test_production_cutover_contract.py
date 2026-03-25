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
