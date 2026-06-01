from __future__ import annotations

from datetime import date

from src.core.bank_demo_proof.model_common import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
)
from src.core.bank_demo_proof.scenario_models import (
    AdvisoryDemoScenarioContract,
    DemoScenarioStep,
)

RFC28_SCENARIO_CONTRACT_REF = "lotus-advise://rfc0028/scenario-contract.v1.json"

RFC28_SOURCE_PRODUCT_REFS: tuple[str, ...] = (
    "ProposalNarrativeEvidence:v1",
    "AdvisoryProposalMemoEvidencePack:v1",
    "AdvisoryPolicyEvaluationRecord:v1",
    "AdvisorCockpitOperatingSnapshot:v1",
    "AdvisoryActionItemRegister:v1",
    "AdvisoryCopilotInteractionRecord:v1",
)

RFC28_UNSUPPORTED_BOUNDARIES: tuple[str, ...] = (
    "Client-ready publication remains blocked until publication controls, supported-claim review, "
    "Gateway/Workbench proof, and document controls are implemented and validated.",
    "External client communication is not owned or approved by RFC-0028 backend proof capture.",
    "OMS order, fill, settlement, and downstream execution system-of-record status remain outside "
    "lotus-advise ownership.",
    "RFP/security pack claims are not promoted until commercial artifacts are reviewed against the "
    "supported-claim register and implementation evidence.",
)


def build_default_scenario_contract() -> AdvisoryDemoScenarioContract:
    return AdvisoryDemoScenarioContract(
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        governed_as_of_date=date(2026, 5, 28),
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        required_evidence_markers=[RFC28_CANONICAL_PROOF_MARKER],
        required_source_products=list(RFC28_SOURCE_PRODUCT_REFS),
        unsupported_boundaries=list(RFC28_UNSUPPORTED_BOUNDARIES),
        steps=[
            DemoScenarioStep(
                step_id="advisor_cockpit_operating_snapshot",
                title="Advisor reviews source-backed cockpit actions",
                owner_repository="lotus-advise",
                required_evidence_refs=["proof.assets.sanitized_runtime_summary"],
                required_workbench_panels=["advisory.advisor_cockpit"],
            ),
            DemoScenarioStep(
                step_id="proposal_lifecycle_and_decision_paths",
                title="Advisor validates proposal lifecycle, decisions, and alternatives",
                owner_repository="lotus-advise",
                required_evidence_refs=["proof.assets.material_field_review"],
            ),
            DemoScenarioStep(
                step_id="narrative_memo_policy_evidence",
                title="Advisor reviews narrative, memo, and policy evidence",
                owner_repository="lotus-advise",
                required_evidence_refs=[
                    "proof.assets.sanitized_runtime_summary",
                    "proof.assets.journey_integration_proof_summary",
                ],
                required_workbench_panels=[
                    "proposal.memo_evidence_pack",
                    "advisory.suitability_review",
                ],
            ),
            DemoScenarioStep(
                step_id="degraded_source_readiness",
                title="Advisor sees degraded-source boundaries without unsupported approval claims",
                owner_repository="lotus-advise",
                required_evidence_refs=["proof.assets.material_field_review"],
            ),
        ],
    )
