from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path
from types import ModuleType


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _platform_root(repo_root: Path) -> Path:
    return repo_root.parent / "lotus-platform"


def _platform_contract_dir(platform_root: Path) -> Path:
    return platform_root / "platform-contracts" / "domain-data-products"


def _platform_vocabulary_dir(platform_root: Path) -> Path:
    return platform_root / "platform-contracts" / "domain-vocabulary"


def _local_contract_dir(repo_root: Path) -> Path:
    return repo_root / "contracts" / "domain-data-products"


def _load_platform_validator(platform_contract_dir: Path) -> ModuleType:
    validator_path = platform_contract_dir / "validate_domain_data_product_contracts.py"
    spec = importlib.util.spec_from_file_location(
        "lotus_platform_domain_product_validator",
        validator_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load platform validator from {validator_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _copy_tree_contents(source: Path, destination: Path, pattern: str) -> int:
    copied = 0
    for path in sorted(source.glob(pattern)):
        if path.is_file():
            shutil.copy2(path, destination / path.name)
            copied += 1
    return copied


def _stage_validation_inputs(
    *,
    local_contract_dir: Path,
    platform_contract_dir: Path,
    platform_vocabulary_dir: Path,
    stage_root: Path,
) -> tuple[Path, int, int]:
    staged_contract_dir = stage_root / "domain-data-products"
    staged_vocabulary_dir = stage_root / "domain-vocabulary"
    staged_contract_dir.mkdir(parents=True, exist_ok=True)
    staged_vocabulary_dir.mkdir(parents=True, exist_ok=True)

    platform_contract_count = _copy_tree_contents(
        platform_contract_dir,
        staged_contract_dir,
        "*-*.v1.json",
    )
    local_contract_count = _copy_tree_contents(
        local_contract_dir,
        staged_contract_dir,
        "*-*.v1.json",
    )

    for registry_name in (
        "domain-data-product-semantics.v1.json",
        "domain-data-product-trust-metadata.v1.json",
    ):
        shutil.copy2(
            platform_vocabulary_dir / registry_name,
            staged_vocabulary_dir / registry_name,
        )

    return staged_contract_dir, local_contract_count, platform_contract_count


def validate_repo_native_declarations(
    *,
    repo_root: Path | None = None,
) -> tuple[list[str], int, int]:
    effective_repo_root = repo_root or _repo_root()
    platform_root = _platform_root(effective_repo_root)
    local_contract_dir = _local_contract_dir(effective_repo_root)
    platform_contract_dir = _platform_contract_dir(platform_root)
    platform_vocabulary_dir = _platform_vocabulary_dir(platform_root)

    validator = _load_platform_validator(platform_contract_dir)

    with tempfile.TemporaryDirectory(prefix="lotus-advise-domain-products-") as temp_dir:
        staged_contract_dir, local_count, platform_count = _stage_validation_inputs(
            local_contract_dir=local_contract_dir,
            platform_contract_dir=platform_contract_dir,
            platform_vocabulary_dir=platform_vocabulary_dir,
            stage_root=Path(temp_dir),
        )
        issues = validator.validate_contract_directory(staged_contract_dir)
        return issues, local_count, platform_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate lotus-advise repo-native domain product declarations "
            "against platform registries."
        )
    )
    parser.parse_args(argv)

    issues, local_count, platform_count = validate_repo_native_declarations()
    if issues:
        for issue in issues:
            print(issue)
        return 1

    print(
        "Validated "
        f"{local_count} lotus-advise declaration files against "
        f"{platform_count} platform declaration files and the platform trust registries."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
