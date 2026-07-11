from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from scripts import postgres_migration_rollout_contract as rollout_contract
from scripts.postgres_migration_rollout_contract import (
    DEFAULT_CONTRACT_PATH,
    build_rehearsal_evidence,
    load_contract,
    validate_contract,
)


def test_current_postgres_migration_rollout_contract_passes() -> None:
    assert validate_contract(load_contract(DEFAULT_CONTRACT_PATH)) == []


def test_rehearsal_evidence_includes_all_namespaces() -> None:
    evidence = build_rehearsal_evidence(load_contract(DEFAULT_CONTRACT_PATH))

    assert evidence["schema_version"] == "lotus.advise.postgres-migration-rehearsal-evidence.v1"
    assert {namespace["namespace_key"] for namespace in evidence["namespaces"]} == {
        "proposals",
        "advisory_copilot",
        "policy_packs",
    }
    assert any(migration["namespace_key"] == "policy_packs" for migration in evidence["migrations"])


def test_contract_rejects_missing_migration_metadata() -> None:
    contract = load_contract(DEFAULT_CONTRACT_PATH)
    mutated = deepcopy(contract)
    mutated["migrations"] = [
        migration
        for migration in mutated["migrations"]
        if not (migration["namespace_key"] == "policy_packs" and migration["version"] == "0001")
    ]

    failures = validate_contract(mutated)

    assert "Migration policy_packs:0001 is missing rollout metadata." in failures


def test_contract_rejects_missing_rollback_metadata() -> None:
    contract = load_contract(DEFAULT_CONTRACT_PATH)
    mutated = deepcopy(contract)
    del mutated["migrations"][0]["rollback"]

    failures = validate_contract(mutated)

    assert "Migration proposals:0001 missing required field: rollback." in failures
    assert "Migration proposals:0001 rollback must be an object." in failures


def test_contract_rejects_index_without_online_behavior() -> None:
    contract = load_contract(DEFAULT_CONTRACT_PATH)
    mutated = deepcopy(contract)
    index_migration = next(
        migration
        for migration in mutated["migrations"]
        if migration["namespace_key"] == "proposals" and migration["version"] == "0006"
    )
    index_migration["lock_behavior"]["online_behavior"] = "not_applicable"

    failures = validate_contract(mutated)

    assert "Migration proposals:0006 must document index online/locking behavior." in failures


def test_contract_rejects_migration_runner_missing_namespace(monkeypatch) -> None:
    monkeypatch.setattr(
        rollout_contract,
        "_migration_runner_targets",
        lambda: {"proposals", "advisory_copilot"},
    )

    failures = validate_contract(load_contract(DEFAULT_CONTRACT_PATH))

    assert (
        "scripts/postgres_migrate.py --target all must cover migration directories: "
        "targets=['advisory_copilot', 'proposals'] "
        "actual=['advisory_copilot', 'policy_packs', 'proposals']."
    ) in failures


def test_cli_emits_rehearsal_evidence(tmp_path: Path) -> None:
    output = tmp_path / "postgres-migration-rollout-rehearsal.json"

    assert rollout_contract.main(["--emit-rehearsal-evidence", str(output)]) == 0
    evidence = output.read_text(encoding="utf-8")
    assert "lotus.advise.postgres-migration-rehearsal-evidence.v1" in evidence
    assert "policy_packs" in evidence
