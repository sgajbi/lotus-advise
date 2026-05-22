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
        pytest.skip("lotus-platform validator checkout is not available in this environment")
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
    products = {product["product_name"]: product for product in declaration["products"]}

    assert products["AdvisoryProposalLifecycleRecord"]["identifier_refs"] == [
        "portfolio_id",
        "correlation_id",
    ]
    assert products["AdvisoryProposalLifecycleRecord"]["approved_consumers"] == ["lotus-gateway"]
    tactical_cohort = products["TacticalHouseViewAffectedCohort"]
    assert tactical_cohort["approved_consumers"] == ["lotus-manage"]
    assert tactical_cohort["request_scope"] == {
        "scope_level": "portfolio_set",
        "supports_bulk": True,
    }
    assert tactical_cohort["current_routes"] == ["/advisory/tactical-house-view/cohorts/evaluate"]
    assert (
        "does not discover the global portfolio universe"
        in (tactical_cohort["freshness_policy"]["max_allowed_age_description"])
    )


def test_rfc0023_narrative_product_promotion_remains_bounded_to_evidence() -> None:
    contract_dir = _local_contract_dir(Path(__file__).resolve().parents[3])
    declaration = json.loads(
        (contract_dir / "lotus-advise-products.v1.json").read_text(encoding="utf-8")
    )
    products = {product["product_name"]: product for product in declaration["products"]}

    assert "ProposalNarrative" not in products
    assert "proposal_narrative" not in products
    narrative_evidence = products["ProposalNarrativeEvidence"]
    assert narrative_evidence["product_family"] == "workflow_and_decision_state"
    assert narrative_evidence["authoritative_domain"] == "advisory_workflow"
    assert "generated_at" in narrative_evidence["required_trust_metadata"]
    assert (
        "/advisory/proposals/{proposal_id}/versions/{version_no}/narrative"
        in (narrative_evidence["current_routes"])
    )
    assert not any(
        "client-ready" in route.lower() for route in narrative_evidence["current_routes"]
    )
