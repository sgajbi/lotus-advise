from decimal import Decimal

from src.core.advisory.artifact_models import (
    ProposalArtifact,
    ProposalArtifactAssumptionsAndLimits,
    ProposalArtifactDisclosures,
    ProposalArtifactEngineOutputs,
    ProposalArtifactEvidenceBundle,
    ProposalArtifactEvidenceInputs,
    ProposalArtifactExecutionNote,
    ProposalArtifactFx,
    ProposalArtifactHashes,
    ProposalArtifactInclusionFlag,
    ProposalArtifactPortfolioDelta,
    ProposalArtifactPortfolioImpact,
    ProposalArtifactPortfolioState,
    ProposalArtifactPricingAssumptions,
    ProposalArtifactProductDoc,
    ProposalArtifactSuitabilitySummary,
    ProposalArtifactSummary,
    ProposalArtifactTakeaway,
    ProposalArtifactTrade,
    ProposalArtifactTradeRationale,
    ProposalArtifactTradesAndFunding,
)
from src.core.models import GateDecision, GateDecisionSummary, Money


def test_proposal_artifact_contract_shape():
    state = ProposalArtifactPortfolioState(
        total_value=Money(amount=Decimal("1000"), currency="USD"),
        allocation_by_asset_class=[],
        allocation_by_instrument=[],
    )
    artifact = ProposalArtifact(
        artifact_id="pa_1",
        proposal_run_id="pr_1",
        correlation_id="corr_1",
        created_at="2026-02-19T12:00:00+00:00",
        status="READY",
        gate_decision=GateDecision(
            gate="CLIENT_CONSENT_REQUIRED",
            recommended_next_step="REQUEST_CLIENT_CONSENT",
            reasons=[],
            summary=GateDecisionSummary(
                hard_fail_count=0,
                soft_fail_count=0,
                new_high_suitability_count=0,
                new_medium_suitability_count=0,
            ),
        ),
        summary=ProposalArtifactSummary(
            title="Proposal for pf_1",
            objective_tags=["PORTFOLIO_MAINTENANCE"],
            advisor_notes=[],
            recommended_next_step="CLIENT_CONSENT",
            key_takeaways=[
                ProposalArtifactTakeaway(code="STATUS", value="Proposal status is READY.")
            ],
        ),
        portfolio_impact=ProposalArtifactPortfolioImpact(
            before=state,
            after=state,
            delta=ProposalArtifactPortfolioDelta(
                total_value_delta=Money(amount=Decimal("0"), currency="USD"),
                largest_weight_changes=[],
            ),
            reconciliation=None,
        ),
        trades_and_funding=ProposalArtifactTradesAndFunding(
            trade_list=[
                ProposalArtifactTrade(
                    intent_id="oi_1",
                    type="SECURITY_TRADE",
                    instrument_id="EQ_1",
                    side="BUY",
                    quantity="1",
                    estimated_notional=Money(amount=Decimal("100"), currency="USD"),
                    estimated_notional_base=Money(amount=Decimal("100"), currency="USD"),
                    dependencies=["oi_fx_1"],
                    rationale=ProposalArtifactTradeRationale(
                        code="MANUAL_PROPOSAL",
                        message="Manual advisory trade from proposal simulation.",
                    ),
                )
            ],
            fx_list=[
                ProposalArtifactFx(
                    intent_id="oi_fx_1",
                    pair="USD/SGD",
                    buy_amount="100",
                    sell_amount_estimated="135",
                    rate="1.3500",
                )
            ],
            ordering_policy="CASH_FLOW->SELL->FX->BUY",
            execution_notes=[
                ProposalArtifactExecutionNote(
                    code="DEPENDENCY",
                    text="One or more BUY intents depend on generated FX intents.",
                )
            ],
        ),
        suitability_summary=ProposalArtifactSuitabilitySummary(
            status="NOT_AVAILABLE",
            new_issues=0,
            resolved_issues=0,
            persistent_issues=0,
            highest_severity_new=None,
            highlights=[],
            issues=[],
        ),
        assumptions_and_limits=ProposalArtifactAssumptionsAndLimits(
            pricing=ProposalArtifactPricingAssumptions(
                market_data_snapshot_id="md_1",
                prices_as_of="md_1",
                fx_as_of="md_1",
                valuation_mode="CALCULATED",
            ),
            costs_and_fees=ProposalArtifactInclusionFlag(
                included=False,
                notes="Transaction costs are not modeled.",
            ),
            tax=ProposalArtifactInclusionFlag(
                included=False,
                notes="Tax is not modeled.",
            ),
            execution=ProposalArtifactInclusionFlag(
                included=False,
                notes="Execution slippage is not modeled.",
            ),
        ),
        disclosures=ProposalArtifactDisclosures(
            risk_disclaimer="This proposal is based on market-data snapshots.",
            product_docs=[
                ProposalArtifactProductDoc(
                    instrument_id="EQ_1",
                    doc_ref="KID/FactSheet placeholder",
                )
            ],
        ),
        evidence_bundle=ProposalArtifactEvidenceBundle(
            inputs=ProposalArtifactEvidenceInputs(
                portfolio_snapshot={"portfolio_id": "pf_1", "base_currency": "USD"},
                market_data_snapshot={"prices": [], "fx_rates": []},
                shelf_entries=[],
                options={"enable_proposal_simulation": True},
                proposed_cash_flows=[],
                proposed_trades=[],
                reference_model=None,
            ),
            engine_outputs=ProposalArtifactEngineOutputs(proposal_result={"status": "READY"}),
            hashes=ProposalArtifactHashes(
                request_hash="sha256:abc",
                artifact_hash="sha256:def",
            ),
            engine_version="0.1.0",
        ),
    )

    assert artifact.status == "READY"
    assert artifact.evidence_bundle.hashes.request_hash.startswith("sha256:")
