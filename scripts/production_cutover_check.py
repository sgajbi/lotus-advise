import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate production persistence contract and migration readiness."
    )
    parser.add_argument(
        "--check-migrations",
        action="store_true",
        help="Require all checked-in postgres migrations to be applied for both namespaces.",
    )
    args = parser.parse_args()

    from src.api.production_cutover_contract import validate_production_cutover_contract

    validate_production_cutover_contract(check_migrations=args.check_migrations)
    print("Production cutover contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
