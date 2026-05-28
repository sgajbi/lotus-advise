from __future__ import annotations

from scripts.postgres_migrate import _resolve_targets


def test_postgres_migrate_all_includes_copilot_namespace() -> None:
    assert _resolve_targets(
        "all",
        proposals_dsn="postgres://proposal",
        advisory_copilot_dsn="postgres://copilot",
    ) == [
        ("proposals", "postgres://proposal"),
        ("advisory_copilot", "postgres://copilot"),
    ]


def test_postgres_migrate_can_apply_copilot_namespace_independently() -> None:
    assert _resolve_targets(
        "advisory_copilot",
        proposals_dsn="postgres://proposal",
        advisory_copilot_dsn="postgres://copilot",
    ) == [("advisory_copilot", "postgres://copilot")]
