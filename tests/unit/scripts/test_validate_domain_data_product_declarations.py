import json
from pathlib import Path

import pytest

from scripts.validate_domain_data_product_declarations import (
    _local_contract_dir,
    platform_validation_dependencies_available,
    validate_repo_native_declarations,
)


def test_repo_native_domain_data_product_validation_passes() -> None:
    if not platform_validation_dependencies_available():
        pytest.skip(
            "lotus-platform validator checkout is not available in this environment"
        )
    issues, local_count, platform_count = validate_repo_native_declarations()

    assert issues == []
    assert local_count == 2
    assert platform_count >= 5


def test_local_contract_directory_contains_expected_repo_native_files() -> None:
    contract_dir = _local_contract_dir(Path(__file__).resolve().parents[3])

    assert (contract_dir / "lotus-advise-products.v1.json").is_file()
    assert (contract_dir / "lotus-advise-consumers.v1.json").is_file()


def test_wave_one_advise_declaration_is_conservative_and_transitional() -> None:
    contract_dir = _local_contract_dir(Path(__file__).resolve().parents[3])
    declaration = json.loads(
        (contract_dir / "lotus-advise-products.v1.json").read_text(encoding="utf-8")
    )

    assert declaration["products"][0]["product_name"] == "AdvisoryProposalLifecycleRecord"
    assert declaration["products"][0]["identifier_refs"] == [
        "portfolio_id",
        "correlation_id",
    ]
    assert declaration["products"][0]["approved_consumers"] == ["lotus-gateway"]
