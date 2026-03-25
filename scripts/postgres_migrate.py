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
        description="Apply forward-only PostgreSQL migrations for lotus-advise proposal stores."
    )
    parser.add_argument(
        "--target",
        choices=["proposals"],
        default="proposals",
        help="Migration target namespace.",
    )
    parser.add_argument(
        "--proposals-dsn",
        default=os.getenv("PROPOSAL_POSTGRES_DSN", "").strip(),
        help="PostgreSQL DSN for advisory proposal migrations.",
    )
    args = parser.parse_args()

    if find_spec("psycopg") is None:
        raise RuntimeError("POSTGRES_MIGRATION_DRIVER_MISSING")
    import psycopg
    from psycopg.rows import dict_row

    from src.infrastructure.postgres_migrations import apply_postgres_migrations

    targets = _resolve_targets(args.target, args.proposals_dsn)
    for namespace, dsn in targets:
        if not dsn:
            raise RuntimeError(f"POSTGRES_MIGRATION_DSN_REQUIRED:{namespace}")
        with psycopg.connect(dsn, row_factory=dict_row) as connection:
            apply_postgres_migrations(connection=connection, namespace=namespace)
        print(f"Applied migrations for namespace={namespace}")
    return 0


def _resolve_targets(target: str, proposals_dsn: str) -> list[tuple[str, str]]:
    _ = target
    return [("proposals", proposals_dsn)]


if __name__ == "__main__":
    raise SystemExit(main())
