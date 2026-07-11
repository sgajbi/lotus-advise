import argparse
import os
import sys
from importlib.util import find_spec
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply forward-only PostgreSQL migrations for lotus-advise stores."
    )
    parser.add_argument(
        "--target",
        choices=["all", "proposals", "advisory_copilot", "policy_packs"],
        default="all",
        help="Migration target namespace.",
    )
    parser.add_argument(
        "--proposals-dsn",
        default=os.getenv("PROPOSAL_POSTGRES_DSN", "").strip(),
        help="PostgreSQL DSN for advisory proposal migrations.",
    )
    parser.add_argument(
        "--advisory-copilot-dsn",
        default=(
            os.getenv("ADVISORY_COPILOT_POSTGRES_DSN", "").strip()
            or os.getenv("PROPOSAL_POSTGRES_DSN", "").strip()
        ),
        help="PostgreSQL DSN for advisory copilot migrations.",
    )
    parser.add_argument(
        "--policy-postgres-dsn",
        default=(
            os.getenv("POLICY_POSTGRES_DSN", "").strip()
            or os.getenv("PROPOSAL_POSTGRES_DSN", "").strip()
        ),
        help="PostgreSQL DSN for policy pack migrations.",
    )
    args = parser.parse_args()

    if find_spec("psycopg") is None:
        raise RuntimeError("POSTGRES_MIGRATION_DRIVER_MISSING")
    import psycopg
    from psycopg.rows import dict_row

    from src.infrastructure.postgres_migrations import apply_postgres_migrations

    targets = _resolve_targets(
        args.target,
        proposals_dsn=args.proposals_dsn,
        advisory_copilot_dsn=args.advisory_copilot_dsn,
        policy_packs_dsn=args.policy_postgres_dsn,
    )
    for namespace, dsn in targets:
        if not dsn:
            raise RuntimeError(f"POSTGRES_MIGRATION_DSN_REQUIRED:{namespace}")
        with psycopg.connect(dsn, row_factory=dict_row) as connection:
            apply_postgres_migrations(connection=connection, namespace=namespace)
        print(f"Applied migrations for namespace={namespace}")
    return 0


def _resolve_targets(
    target: str,
    *,
    proposals_dsn: str,
    advisory_copilot_dsn: str,
    policy_packs_dsn: str,
) -> list[tuple[str, str]]:
    targets = {
        "proposals": proposals_dsn,
        "advisory_copilot": advisory_copilot_dsn,
        "policy_packs": policy_packs_dsn,
    }
    if target == "all":
        return list(targets.items())
    return [(target, targets[target])]


if __name__ == "__main__":
    raise SystemExit(main())
