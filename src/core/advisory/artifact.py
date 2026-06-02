from datetime import datetime, timezone
from typing import cast

from src.core.advisory.artifact_models import (
    ProposalArtifact,
    ProposalArtifactAssumptionsAndLimits,
    ProposalArtifactDisclosures,
    ProposalArtifactEngineOutputs,
    ProposalArtifactEvidenceBundle,
    ProposalArtifactEvidenceInputs,
    ProposalArtifactHashes,
    ProposalArtifactInclusionFlag,
    ProposalArtifactPortfolioDelta,
    ProposalArtifactPortfolioImpact,
    ProposalArtifactPricingAssumptions,
    ProposalArtifactProductDoc,
    ProposalArtifactSummary,
)
from src.core.advisory.artifact_portfolio import (
    build_portfolio_state_payload,
    largest_weight_changes,
)
from src.core.advisory.artifact_review import (
    build_risk_lens_summary,
    build_suitability_summary,
)
from src.core.advisory.artifact_summary import (
    build_takeaways,
    resolve_next_step,
    resolve_objective_tags,
)
from src.core.advisory.artifact_trades import build_trades_and_funding
from src.core.advisory.decision_summary import build_proposal_decision_summary
from src.core.advisory.narrative import build_deterministic_proposal_narrative
from src.core.common.canonical import hash_canonical_payload, strip_keys
from src.core.common.workflow_gates import evaluate_gate_decision
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposal_result_models import ProposalResult


def build_proposal_artifact(
    *,
    request: ProposalSimulateRequest,
    proposal_result: ProposalResult,
    created_at: str | None = None,
) -> ProposalArtifact:
    before_state = proposal_result.before
    after_state = proposal_result.after_simulated
    weight_changes = largest_weight_changes(
        before_state,
        after_state,
        limit=request.options.drift_top_contributors_limit,
    )

    assumptions = ProposalArtifactAssumptionsAndLimits(
        pricing=ProposalArtifactPricingAssumptions(
            market_data_snapshot_id=proposal_result.lineage.market_data_snapshot_id,
            prices_as_of=proposal_result.lineage.market_data_snapshot_id,
            fx_as_of=proposal_result.lineage.market_data_snapshot_id,
            valuation_mode=request.options.valuation_mode.value,
        ),
        costs_and_fees=ProposalArtifactInclusionFlag(
            included=False,
            notes="Transaction costs, fees, and bid/ask spreads are not modeled.",
        ),
        tax=ProposalArtifactInclusionFlag(
            included=False,
            notes="Tax impact is not modeled in the proposal artifact.",
        ),
        execution=ProposalArtifactInclusionFlag(
            included=False,
            notes="Execution timing and slippage are not modeled.",
        ),
    )

    traded_instruments = sorted(
        {
            intent.instrument_id
            for intent in proposal_result.intents
            if intent.intent_type == "SECURITY_TRADE"
        }
    )

    artifact = ProposalArtifact(
        gate_decision=(
            proposal_result.gate_decision
            or evaluate_gate_decision(
                status=proposal_result.status,
                rule_results=proposal_result.rule_results,
                suitability=proposal_result.suitability,
                diagnostics=proposal_result.diagnostics,
                options=request.options,
                default_requires_client_consent=True,
            )
        ),
        proposal_decision_summary=(
            proposal_result.proposal_decision_summary
            or build_proposal_decision_summary(proposal_result)
        ),
        proposal_alternatives=(
            proposal_result.proposal_alternatives.model_copy(deep=True)
            if proposal_result.proposal_alternatives is not None
            else None
        ),
        artifact_id=proposal_result.proposal_run_id.replace("pr_", "pa_", 1),
        proposal_run_id=proposal_result.proposal_run_id,
        correlation_id=proposal_result.correlation_id,
        created_at=created_at or datetime.now(timezone.utc).isoformat(),
        status=proposal_result.status,
        summary=ProposalArtifactSummary(
            title=f"Proposal for {request.portfolio_snapshot.portfolio_id}",
            objective_tags=resolve_objective_tags(request=request, result=proposal_result),
            advisor_notes=[],
            recommended_next_step=resolve_next_step(proposal_result),
            key_takeaways=build_takeaways(request=request, result=proposal_result),
        ),
        portfolio_impact=ProposalArtifactPortfolioImpact(
            before=build_portfolio_state_payload(before_state),
            after=build_portfolio_state_payload(after_state),
            delta=ProposalArtifactPortfolioDelta(
                total_value_delta={
                    "amount": after_state.total_value.amount - before_state.total_value.amount,
                    "currency": before_state.total_value.currency,
                },
                largest_weight_changes=weight_changes,
            ),
            reconciliation=(
                proposal_result.reconciliation.model_dump(mode="json")
                if proposal_result.reconciliation is not None
                else None
            ),
        ),
        trades_and_funding=build_trades_and_funding(request=request, result=proposal_result),
        risk_lens=build_risk_lens_summary(proposal_result),
        suitability_summary=build_suitability_summary(request=request, result=proposal_result),
        assumptions_and_limits=assumptions,
        disclosures=ProposalArtifactDisclosures(
            risk_disclaimer=(
                "This proposal is based on market-data snapshots and does not guarantee "
                "future performance."
            ),
            product_docs=[
                ProposalArtifactProductDoc(
                    instrument_id=instrument_id,
                    doc_ref="KID/FactSheet reference pending source confirmation",
                )
                for instrument_id in traded_instruments
            ],
        ),
        evidence_bundle=ProposalArtifactEvidenceBundle(
            inputs=ProposalArtifactEvidenceInputs(
                portfolio_snapshot=request.portfolio_snapshot.model_dump(mode="json"),
                market_data_snapshot=request.market_data_snapshot.model_dump(mode="json"),
                shelf_entries=[entry.model_dump(mode="json") for entry in request.shelf_entries],
                options=request.options.model_dump(mode="json"),
                proposed_cash_flows=[
                    item.model_dump(mode="json") for item in request.proposed_cash_flows
                ],
                proposed_trades=[item.model_dump(mode="json") for item in request.proposed_trades],
                reference_model=(
                    request.reference_model.model_dump(mode="json")
                    if request.reference_model is not None
                    else None
                ),
            ),
            engine_outputs=ProposalArtifactEngineOutputs(
                proposal_result=proposal_result.model_dump(mode="json")
            ),
            hashes=ProposalArtifactHashes(
                request_hash=proposal_result.lineage.request_hash,
                artifact_hash="",
            ),
            engine_version=proposal_result.lineage.engine_version or "unknown",
        ),
    )
    payload = artifact.model_dump(mode="json")
    base_canonical_payload = strip_keys(
        payload, exclude={"created_at", "artifact_hash", "proposal_narrative"}
    )
    base_artifact_hash = hash_canonical_payload(base_canonical_payload)
    payload["evidence_bundle"]["hashes"]["artifact_hash"] = base_artifact_hash
    artifact = ProposalArtifact.model_validate(payload)

    if request.narrative_request is not None:
        narrative = build_deterministic_proposal_narrative(
            artifact=artifact,
            request=request.narrative_request,
        )
        payload = artifact.model_dump(mode="json")
        payload["proposal_narrative"] = narrative.model_dump(mode="json")
        narrative_canonical_payload = strip_keys(payload, exclude={"created_at", "artifact_hash"})
        payload["evidence_bundle"]["hashes"]["artifact_hash"] = hash_canonical_payload(
            narrative_canonical_payload
        )

    return cast(ProposalArtifact, ProposalArtifact.model_validate(payload))
