from __future__ import annotations

from scripts.postgres_migrate import _resolve_targets


def test_postgres_migrate_all_includes_copilot_namespace() -> None:
    assert _resolve_targets(
        "all",
        proposals_dsn="postgres://proposal",
        advisory_copilot_dsn="postgres://copilot",
        policy_packs_dsn="postgres://policy",
        workspace_dsn="postgres://workspace",
    ) == [
        ("proposals", "postgres://proposal"),
        ("advisory_copilot", "postgres://copilot"),
        ("policy_packs", "postgres://policy"),
        ("workspace", "postgres://workspace"),
    ]


def test_postgres_migrate_can_apply_copilot_namespace_independently() -> None:
    assert _resolve_targets(
        "advisory_copilot",
        proposals_dsn="postgres://proposal",
        advisory_copilot_dsn="postgres://copilot",
        policy_packs_dsn="postgres://policy",
        workspace_dsn="postgres://workspace",
    ) == [("advisory_copilot", "postgres://copilot")]


def test_postgres_migrate_can_apply_policy_pack_namespace_independently() -> None:
    assert _resolve_targets(
        "policy_packs",
        proposals_dsn="postgres://proposal",
        advisory_copilot_dsn="postgres://copilot",
        policy_packs_dsn="postgres://policy",
        workspace_dsn="postgres://workspace",
    ) == [("policy_packs", "postgres://policy")]


def test_postgres_migrate_can_apply_workspace_namespace_independently() -> None:
    assert _resolve_targets(
        "workspace",
        proposals_dsn="postgres://proposal",
        advisory_copilot_dsn="postgres://copilot",
        policy_packs_dsn="postgres://policy",
        workspace_dsn="postgres://workspace",
    ) == [("workspace", "postgres://workspace")]
