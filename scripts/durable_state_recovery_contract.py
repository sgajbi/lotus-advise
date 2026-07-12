"""Validate lotus-advise durable-state recovery scope and drill evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = REPO_ROOT / "docs" / "standards" / "advisory-durable-state-recovery.v1.json"
MIGRATIONS_ROOT = REPO_ROOT / "src" / "infrastructure" / "postgres_migrations"
MAX_RTO_MINUTES = 30
MAX_RPO_MINUTES = 15
REQUIRED_NAMESPACE_FIELDS = (
    "namespace_key",
    "owner",
    "dsn_env",
    "migration_target",
    "backup_scope",
    "retention_class",
    "rto_minutes",
    "rpo_minutes",
    "durable_records",
    "restore_checks",
    "replay_quarantine",
    "escalation_owner",
)
REQUIRED_RESTORE_CHECK_FIELDS = ("check_key", "command", "evidence_path")
REQUIRED_REPLAY_QUARANTINE_FIELDS = ("safe_resume_condition", "quarantine_condition")
REQUIRED_DRILL_PROFILE_FIELDS = (
    "profile_key",
    "environment_scope",
    "restore_command",
    "validation_commands",
    "evidence_path",
    "stop_criteria",
    "resume_criteria",
)


def load_contract(path: Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def validate_contract(
    contract: dict[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
) -> list[str]:
    failures: list[str] = []
    if contract.get("schema_version") != "lotus.advise.durable-state-recovery.v1":
        failures.append("Contract schema_version must be lotus.advise.durable-state-recovery.v1.")
    if contract.get("service_name") != "lotus-advise":
        failures.append("Contract service_name must be lotus-advise.")

    _validate_recovery_targets(contract.get("recovery_targets"), failures)
    namespaces = _object_list(contract, "durable_namespaces", "namespace_key", failures)
    actual_namespaces = _actual_migration_namespaces(repo_root)
    if set(namespaces) != actual_namespaces:
        failures.append(
            "Durable recovery namespaces must match migration directories: "
            f"contract={sorted(namespaces)} actual={sorted(actual_namespaces)}."
        )

    for namespace_key, namespace in namespaces.items():
        failures.extend(_validate_namespace(namespace_key, namespace))

    _validate_downstream_dependencies(contract.get("downstream_replay_dependencies"), failures)
    _validate_drill_profiles(contract.get("restore_drill_profiles"), failures)
    return failures


def build_drill_evidence(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "lotus.advise.durable-state-recovery-drill-evidence.v1",
        "service_name": contract.get("service_name"),
        "contract_path": "docs/standards/advisory-durable-state-recovery.v1.json",
        "recovery_targets": contract.get("recovery_targets", {}),
        "durable_namespaces": [
            {
                "namespace_key": namespace.get("namespace_key"),
                "owner": namespace.get("owner"),
                "dsn_env": namespace.get("dsn_env"),
                "migration_target": namespace.get("migration_target"),
                "restore_check_keys": [
                    check.get("check_key") for check in namespace.get("restore_checks", [])
                ],
                "replay_quarantine": namespace.get("replay_quarantine", {}),
            }
            for namespace in contract.get("durable_namespaces", [])
        ],
        "restore_drill_profiles": contract.get("restore_drill_profiles", []),
        "downstream_replay_dependencies": contract.get("downstream_replay_dependencies", []),
    }


def _validate_recovery_targets(targets: object, failures: list[str]) -> None:
    if not isinstance(targets, dict):
        failures.append("recovery_targets must be an object.")
        return
    if targets.get("rto_minutes") != MAX_RTO_MINUTES:
        failures.append(f"recovery_targets.rto_minutes must be {MAX_RTO_MINUTES}.")
    if targets.get("rpo_minutes") != MAX_RPO_MINUTES:
        failures.append(f"recovery_targets.rpo_minutes must be {MAX_RPO_MINUTES}.")
    if not targets.get("certification_boundary"):
        failures.append("recovery_targets.certification_boundary must be documented.")


def _validate_namespace(namespace_key: str, namespace: dict[str, Any]) -> list[str]:
    owner = f"Namespace {namespace_key}"
    failures = _missing_fields(owner, namespace, REQUIRED_NAMESPACE_FIELDS)
    if namespace.get("migration_target") != namespace_key:
        failures.append(f"{owner} migration_target must match namespace_key.")
    if namespace.get("rto_minutes") != MAX_RTO_MINUTES:
        failures.append(f"{owner} rto_minutes must be {MAX_RTO_MINUTES}.")
    if namespace.get("rpo_minutes") != MAX_RPO_MINUTES:
        failures.append(f"{owner} rpo_minutes must be {MAX_RPO_MINUTES}.")
    failures.extend(_validate_non_empty_string_list(owner, namespace, "durable_records"))
    failures.extend(_validate_restore_checks(owner, namespace.get("restore_checks")))
    failures.extend(
        _validate_nested_object(
            f"{owner} replay_quarantine",
            namespace.get("replay_quarantine"),
            REQUIRED_REPLAY_QUARANTINE_FIELDS,
        )
    )
    return failures


def _validate_restore_checks(owner: str, checks: object) -> list[str]:
    if not isinstance(checks, list) or not checks:
        return [f"{owner} restore_checks must be a non-empty list."]
    failures: list[str] = []
    seen: set[str] = set()
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            failures.append(f"{owner} restore_checks[{index}] must be an object.")
            continue
        check_key = check.get("check_key")
        if isinstance(check_key, str) and check_key in seen:
            failures.append(f"{owner} contains duplicate restore check: {check_key}.")
        if isinstance(check_key, str):
            seen.add(check_key)
        failures.extend(
            _validate_nested_object(
                f"{owner} restore_checks[{index}]",
                check,
                REQUIRED_RESTORE_CHECK_FIELDS,
            )
        )
    return failures


def _validate_downstream_dependencies(dependencies: object, failures: list[str]) -> None:
    if not isinstance(dependencies, list) or not dependencies:
        failures.append("downstream_replay_dependencies must be a non-empty list.")
        return
    for index, dependency in enumerate(dependencies):
        failures.extend(
            _validate_nested_object(
                f"downstream_replay_dependencies[{index}]",
                dependency,
                ("dependency_key", "owner", "quarantine_rule"),
            )
        )


def _validate_drill_profiles(profiles: object, failures: list[str]) -> None:
    if not isinstance(profiles, list) or not profiles:
        failures.append("restore_drill_profiles must be a non-empty list.")
        return
    for index, profile in enumerate(profiles):
        failures.extend(
            _validate_nested_object(
                f"restore_drill_profiles[{index}]",
                profile,
                REQUIRED_DRILL_PROFILE_FIELDS,
            )
        )
        if isinstance(profile, dict):
            failures.extend(
                _validate_non_empty_string_list(
                    f"restore_drill_profiles[{index}]",
                    profile,
                    "validation_commands",
                )
            )
            failures.extend(
                _validate_non_empty_string_list(
                    f"restore_drill_profiles[{index}]",
                    profile,
                    "stop_criteria",
                )
            )
            failures.extend(
                _validate_non_empty_string_list(
                    f"restore_drill_profiles[{index}]",
                    profile,
                    "resume_criteria",
                )
            )


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


def _missing_fields(
    owner: str, item: dict[str, Any], required_fields: tuple[str, ...]
) -> list[str]:
    return [
        f"{owner} missing required field: {field}."
        for field in required_fields
        if field not in item
    ]


def _validate_nested_object(
    owner: str,
    item: object,
    required_fields: tuple[str, ...],
) -> list[str]:
    if not isinstance(item, dict):
        return [f"{owner} must be an object."]
    return _missing_fields(owner, item, required_fields)


def _validate_non_empty_string_list(
    owner: str,
    item: dict[str, Any],
    field_name: str,
) -> list[str]:
    values = item.get(field_name)
    if not isinstance(values, list) or not values:
        return [f"{owner} {field_name} must be a non-empty list."]
    return [
        f"{owner} {field_name} contains a blank or non-string value."
        for value in values
        if not isinstance(value, str) or not value.strip()
    ]


def _actual_migration_namespaces(repo_root: Path) -> set[str]:
    migration_root = repo_root / "src" / "infrastructure" / "postgres_migrations"
    return {path.name for path in migration_root.iterdir() if path.is_dir()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--emit-drill-evidence", type=Path)
    args = parser.parse_args()

    contract = load_contract(args.contract)
    failures = validate_contract(contract)
    if failures:
        for failure in failures:
            print(failure)
        return 1
    if args.emit_drill_evidence:
        args.emit_drill_evidence.parent.mkdir(parents=True, exist_ok=True)
        args.emit_drill_evidence.write_text(
            json.dumps(build_drill_evidence(contract), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print("Durable state recovery contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
