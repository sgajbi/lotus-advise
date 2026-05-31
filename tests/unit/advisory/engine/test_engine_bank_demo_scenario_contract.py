from __future__ import annotations

from datetime import date

from src.core.bank_demo_proof import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
)
from src.core.bank_demo_proof.scenario_contract import (
    RFC28_SOURCE_PRODUCT_REFS,
    RFC28_UNSUPPORTED_BOUNDARIES,
    build_default_scenario_contract,
)


def test_default_scenario_contract_pins_canonical_identity_and_sources() -> None:
    scenario = build_default_scenario_contract()

    assert scenario.scenario_id == RFC28_CANONICAL_SCENARIO_ID
    assert scenario.primary_portfolio_id == RFC28_CANONICAL_PORTFOLIO_ID
    assert scenario.governed_as_of_date == date(2026, 5, 28)
    assert scenario.proof_marker == RFC28_CANONICAL_PROOF_MARKER
    assert scenario.required_evidence_markers == [RFC28_CANONICAL_PROOF_MARKER]
    assert scenario.required_source_products == list(RFC28_SOURCE_PRODUCT_REFS)
    assert scenario.unsupported_boundaries == list(RFC28_UNSUPPORTED_BOUNDARIES)


def test_default_scenario_contract_uses_governed_workbench_panels() -> None:
    scenario = build_default_scenario_contract()
    panel_refs = {panel for step in scenario.steps for panel in step.required_workbench_panels}
    step_evidence = {step.step_id: set(step.required_evidence_refs) for step in scenario.steps}

    assert panel_refs == {
        "advisory.advisor_cockpit",
        "proposal.memo_evidence_pack",
        "advisory.suitability_review",
    }
    assert "advisor_cockpit" not in panel_refs
    assert step_evidence["proposal_lifecycle_and_decision_paths"] == {
        "proof.assets.material_field_review"
    }
    assert step_evidence["degraded_source_readiness"] == {"proof.assets.material_field_review"}
