from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from scripts.slo_capacity_contract import (
    DEFAULT_CONTRACT_PATH,
    build_smoke_plan,
    load_contract,
    validate_contract,
)


def test_current_slo_capacity_contract_passes() -> None:
    assert validate_contract(load_contract(DEFAULT_CONTRACT_PATH)) == []


def test_smoke_plan_exposes_profiles_and_safe_dimensions() -> None:
    contract = load_contract(DEFAULT_CONTRACT_PATH)

    plan = build_smoke_plan(contract)

    assert plan["schema_version"] == "lotus.advise.slo-capacity-smoke-plan.v1"
    assert plan["service_name"] == "lotus-advise"
    assert plan["profiles"]
    assert "route_template" in plan["metric_dimensions"]
    assert "proposal_id" not in plan["metric_dimensions"]


def test_contract_rejects_unknown_dependency_reference() -> None:
    contract = load_contract(DEFAULT_CONTRACT_PATH)
    mutated = deepcopy(contract)
    mutated["workflow_budgets"][0]["required_dependency_keys"].append("lotus_unknown")

    failures = validate_contract(mutated)

    assert (
        "Workflow budget advisory_proposal_simulation references unknown dependency lotus_unknown."
        in failures
    )


def test_contract_rejects_missing_workflow_budget_field() -> None:
    contract = load_contract(DEFAULT_CONTRACT_PATH)
    mutated = deepcopy(contract)
    del mutated["workflow_budgets"][0]["p99_latency_ms"]

    failures = validate_contract(mutated)

    assert (
        "Workflow budget advisory_proposal_simulation missing required field: p99_latency_ms."
        in failures
    )


def test_contract_rejects_sensitive_metric_dimensions() -> None:
    contract = load_contract(DEFAULT_CONTRACT_PATH)
    mutated = deepcopy(contract)
    mutated["metric_dimensions"]["allowed"].append("proposal_id")

    failures = validate_contract(mutated)

    assert "Allowed metric dimension is high-cardinality or sensitive: proposal_id." in failures


def test_contract_rejects_missing_ai_cost_budget() -> None:
    contract = load_contract(DEFAULT_CONTRACT_PATH)
    mutated = deepcopy(contract)
    lotus_ai = next(
        dependency
        for dependency in mutated["dependency_budgets"]
        if dependency["dependency_key"] == "lotus_ai"
    )
    del lotus_ai["ai_budget"]

    failures = validate_contract(mutated)

    assert "lotus_ai dependency budget must define ai_budget." in failures


def test_contract_rejects_unknown_workflow_in_load_profile() -> None:
    contract = load_contract(DEFAULT_CONTRACT_PATH)
    mutated = deepcopy(contract)
    mutated["load_smoke_profiles"][0]["workflow_keys"].append("unknown_workflow")

    failures = validate_contract(mutated)

    expected_failure = (
        "Load smoke profile local_advisory_capacity_smoke references unknown workflow "
        "unknown_workflow."
    )
    assert expected_failure in failures


def test_cli_emits_smoke_plan(tmp_path: Path) -> None:
    from scripts.slo_capacity_contract import main

    output = tmp_path / "slo-capacity-smoke-plan.json"

    assert main(["--emit-smoke-plan", str(output)]) == 0
    assert output.exists()
    assert "local_advisory_capacity_smoke" in output.read_text(encoding="utf-8")
