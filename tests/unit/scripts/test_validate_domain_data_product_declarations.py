from pathlib import Path

from scripts.validate_domain_data_product_declarations import (
    _local_contract_dir,
    validate_repo_native_declarations,
)


def test_repo_native_domain_data_product_validation_passes() -> None:
    issues, local_count, platform_count = validate_repo_native_declarations()

    assert issues == []
    assert local_count == 2
    assert platform_count >= 5


def test_local_contract_directory_contains_expected_repo_native_files() -> None:
    contract_dir = _local_contract_dir(Path(__file__).resolve().parents[3])

    assert (contract_dir / "lotus-advise-products.v1.json").is_file()
    assert (contract_dir / "lotus-advise-consumers.v1.json").is_file()
