"""Validate Lotus Advise SLO and capacity budget contracts."""

from __future__ import annotations

import argparse
import json
from numbers import Real
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = REPO_ROOT / "docs" / "standards" / "advisory-slo-capacity-budgets.v1.json"
FORBIDDEN_METRIC_DIMENSION_FRAGMENTS = (
    "account",
    "advisor",
    "body",
    "client",
    "correlation",
    "portfolio",
    "proposal",
    "request_id",
    "response",
    "trace",
    "workspace",
)
REQUIRED_WORKFLOW_FIELDS = (
    "workflow_key",
    "route_templates",
    "availability_target_percent",
    "p95_latency_ms",
    "p99_latency_ms",
    "timeout_budget_ms",
    "max_error_rate_percent",
    "max_degraded_rate_percent",
    "max_concurrent_requests",
    "required_dependency_keys",
    "alert_policy_key",
)
REQUIRED_DEPENDENCY_FIELDS = (
    "dependency_key",
    "timeout_budget_ms",
    "retry_attempts",
    "p95_latency_ms",
    "p99_latency_ms",
    "max_error_rate_percent",
    "max_concurrent_operations",
    "rate_limit_per_minute",
)
REQUIRED_LOAD_PROFILE_FIELDS = (
    "profile_key",
    "duration_seconds",
    "ramp_seconds",
    "target_concurrent_requests",
    "workflow_keys",
    "required_evidence",
)


def load_contract(path: Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_contract(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if contract.get("schema_version") != "lotus.advise.slo-capacity-budgets.v1":
        failures.append("Contract schema_version must be lotus.advise.slo-capacity-budgets.v1.")
    if contract.get("service_name") != "lotus-advise":
        failures.append("Contract service_name must be lotus-advise.")

    failures.extend(_validate_metric_dimensions(contract.get("metric_dimensions", {})))

    dependency_budgets = _object_list(contract, "dependency_budgets", "dependency_key", failures)
    workflow_budgets = _object_list(contract, "workflow_budgets", "workflow_key", failures)
    alert_policies = _object_list(contract, "alert_policies", "alert_policy_key", failures)
    load_profiles = _object_list(contract, "load_smoke_profiles", "profile_key", failures)

    dependency_keys = set(dependency_budgets)
    workflow_keys = set(workflow_budgets)
    alert_policy_keys = set(alert_policies)

    for dependency_key, dependency in dependency_budgets.items():
        failures.extend(_validate_dependency_budget(dependency_key, dependency))

    for workflow_key, workflow in workflow_budgets.items():
        failures.extend(
            _validate_workflow_budget(
                workflow_key=workflow_key,
                workflow=workflow,
                dependency_keys=dependency_keys,
                alert_policy_keys=alert_policy_keys,
            )
        )

    for alert_policy_key, alert_policy in alert_policies.items():
        if not alert_policy.get("page_on"):
            failures.append(f"Alert policy {alert_policy_key} must define page_on conditions.")
        if not alert_policy.get("runbook"):
            failures.append(f"Alert policy {alert_policy_key} must define a runbook.")

    for profile_key, profile in load_profiles.items():
        failures.extend(
            _validate_load_profile(
                profile_key=profile_key,
                profile=profile,
                workflow_keys=workflow_keys,
            )
        )

    if "lotus_ai" in dependency_budgets:
        failures.extend(_validate_ai_budget(dependency_budgets["lotus_ai"]))
    else:
        failures.append("Dependency budgets must include lotus_ai.")

    return failures


def build_smoke_plan(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "lotus.advise.slo-capacity-smoke-plan.v1",
        "service_name": contract.get("service_name"),
        "budget_contract": "docs/standards/advisory-slo-capacity-budgets.v1.json",
        "profiles": contract.get("load_smoke_profiles", []),
        "metric_dimensions": contract.get("metric_dimensions", {}).get("allowed", []),
    }


def _object_list(
    contract: dict[str, Any],
    field_name: str,
    key_field: str,
    failures: list[str],
) -> dict[str, dict[str, Any]]:
    raw_items = contract.get(field_name)
    if not isinstance(raw_items, list) or not raw_items:
        failures.append(f"Contract must define non-empty {field_name}.")
        return {}

    items: dict[str, dict[str, Any]] = {}
    for index, raw_item in enumerate(raw_items):
        if not isinstance(raw_item, dict):
            failures.append(f"{field_name}[{index}] must be an object.")
            continue
        key = raw_item.get(key_field)
        if not isinstance(key, str) or not key:
            failures.append(f"{field_name}[{index}] must define {key_field}.")
            continue
        if key in items:
            failures.append(f"{field_name} contains duplicate {key_field}: {key}.")
        items[key] = raw_item
    return items


def _validate_metric_dimensions(metric_dimensions: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    allowed = metric_dimensions.get("allowed", [])
    forbidden = metric_dimensions.get("forbidden", [])
    if not isinstance(allowed, list) or not allowed:
        failures.append("metric_dimensions.allowed must be non-empty.")
        return failures
    if not isinstance(forbidden, list) or not forbidden:
        failures.append("metric_dimensions.forbidden must be non-empty.")

    for dimension in allowed:
        if not isinstance(dimension, str) or not dimension:
            failures.append("metric_dimensions.allowed contains a blank or non-string dimension.")
            continue
        lowered = dimension.lower()
        if any(fragment in lowered for fragment in FORBIDDEN_METRIC_DIMENSION_FRAGMENTS):
            failures.append(
                f"Allowed metric dimension is high-cardinality or sensitive: {dimension}."
            )
    return failures


def _validate_dependency_budget(dependency_key: str, dependency: dict[str, Any]) -> list[str]:
    failures = _missing_fields(
        owner=f"Dependency budget {dependency_key}",
        item=dependency,
        required_fields=REQUIRED_DEPENDENCY_FIELDS,
    )
    failures.extend(
        _positive_number_fields(
            owner=f"Dependency budget {dependency_key}",
            item=dependency,
            fields=(
                "timeout_budget_ms",
                "p95_latency_ms",
                "p99_latency_ms",
                "max_concurrent_operations",
                "rate_limit_per_minute",
            ),
        )
    )
    if dependency.get("retry_attempts", 0) < 0:
        failures.append(f"Dependency budget {dependency_key} retry_attempts must be >= 0.")
    if dependency.get("p99_latency_ms", 0) < dependency.get("p95_latency_ms", 0):
        failures.append(
            f"Dependency budget {dependency_key} p99_latency_ms must be >= p95_latency_ms."
        )
    if not 0 <= dependency.get("max_error_rate_percent", -1) <= 100:
        failures.append(
            f"Dependency budget {dependency_key} max_error_rate_percent must be 0..100."
        )
    return failures


def _validate_workflow_budget(
    *,
    workflow_key: str,
    workflow: dict[str, Any],
    dependency_keys: set[str],
    alert_policy_keys: set[str],
) -> list[str]:
    failures = _missing_fields(
        owner=f"Workflow budget {workflow_key}",
        item=workflow,
        required_fields=REQUIRED_WORKFLOW_FIELDS,
    )
    failures.extend(
        _positive_number_fields(
            owner=f"Workflow budget {workflow_key}",
            item=workflow,
            fields=(
                "availability_target_percent",
                "p95_latency_ms",
                "p99_latency_ms",
                "timeout_budget_ms",
                "max_concurrent_requests",
            ),
        )
    )
    if workflow.get("p99_latency_ms", 0) < workflow.get("p95_latency_ms", 0):
        failures.append(f"Workflow budget {workflow_key} p99_latency_ms must be >= p95_latency_ms.")
    for percent_field in (
        "availability_target_percent",
        "max_error_rate_percent",
        "max_degraded_rate_percent",
    ):
        if not 0 <= workflow.get(percent_field, -1) <= 100:
            failures.append(f"Workflow budget {workflow_key} {percent_field} must be 0..100.")
    route_templates = workflow.get("route_templates", [])
    if not isinstance(route_templates, list) or not route_templates:
        failures.append(f"Workflow budget {workflow_key} must define route_templates.")
    elif any(not isinstance(route, str) or not route.startswith("/") for route in route_templates):
        failures.append(f"Workflow budget {workflow_key} route_templates must be absolute paths.")

    for dependency_key in workflow.get("required_dependency_keys", []):
        if dependency_key not in dependency_keys:
            failures.append(
                f"Workflow budget {workflow_key} references unknown dependency {dependency_key}."
            )
    alert_policy_key = workflow.get("alert_policy_key")
    if alert_policy_key not in alert_policy_keys:
        failures.append(
            f"Workflow budget {workflow_key} references unknown alert policy {alert_policy_key}."
        )
    return failures


def _validate_load_profile(
    *,
    profile_key: str,
    profile: dict[str, Any],
    workflow_keys: set[str],
) -> list[str]:
    failures = _missing_fields(
        owner=f"Load smoke profile {profile_key}",
        item=profile,
        required_fields=REQUIRED_LOAD_PROFILE_FIELDS,
    )
    failures.extend(
        _positive_number_fields(
            owner=f"Load smoke profile {profile_key}",
            item=profile,
            fields=("duration_seconds", "ramp_seconds", "target_concurrent_requests"),
        )
    )
    for workflow_key in profile.get("workflow_keys", []):
        if workflow_key not in workflow_keys:
            failures.append(
                f"Load smoke profile {profile_key} references unknown workflow {workflow_key}."
            )
    if not profile.get("required_evidence"):
        failures.append(f"Load smoke profile {profile_key} must define required_evidence.")
    return failures


def _validate_ai_budget(ai_dependency: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    ai_budget = ai_dependency.get("ai_budget")
    if not isinstance(ai_budget, dict):
        return ["lotus_ai dependency budget must define ai_budget."]
    failures.extend(
        _positive_number_fields(
            owner="lotus_ai ai_budget",
            item=ai_budget,
            fields=(
                "max_input_tokens",
                "max_output_tokens",
                "max_estimated_cost_usd_per_request",
            ),
        )
    )
    if not ai_budget.get("fallback_reason"):
        failures.append("lotus_ai ai_budget must define fallback_reason.")
    return failures


def _missing_fields(
    *,
    owner: str,
    item: dict[str, Any],
    required_fields: tuple[str, ...],
) -> list[str]:
    return [
        f"{owner} missing required field: {field}."
        for field in required_fields
        if field not in item
    ]


def _positive_number_fields(
    *,
    owner: str,
    item: dict[str, Any],
    fields: tuple[str, ...],
) -> list[str]:
    failures: list[str] = []
    for field in fields:
        value = item.get(field)
        if isinstance(value, bool) or not isinstance(value, Real) or value <= 0:
            failures.append(f"{owner} {field} must be a positive number.")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Lotus Advise SLO/capacity budgets.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--emit-smoke-plan", type=Path)
    args = parser.parse_args(argv)

    contract = load_contract(args.contract)
    failures = validate_contract(contract)
    if failures:
        print("SLO capacity contract validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    if args.emit_smoke_plan:
        args.emit_smoke_plan.parent.mkdir(parents=True, exist_ok=True)
        args.emit_smoke_plan.write_text(
            json.dumps(build_smoke_plan(contract), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print("SLO capacity contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
