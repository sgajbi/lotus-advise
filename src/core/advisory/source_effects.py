from __future__ import annotations

from copy import deepcopy
from typing import Annotated, Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from src.core.advisory.simulation_decision_support import build_simulation_decision_support
from src.core.advisory.simulation_intent_plan import SimulationIntentPlan
from src.core.common.canonical import hash_canonical_payload
from src.core.common.simulation_shared import derive_status_from_rules
from src.core.diagnostics_models import DiagnosticsData, LineageData, RuleResult
from src.core.order_intent_models import ProposalOrderIntent
from src.core.proposal_effect_models import Reconciliation
from src.core.proposal_request_models import (
    ProposalSimulateRequest,
    ProposedCashFlow,
    ProposedTrade,
)
from src.core.proposal_result_models import ProposalResult
from src.core.simulation_state_models import ProposalAllocationLens, SimulatedState

ADVISE_DECISION_CALCULATION_VERSION = "lotus-advise.advisory-decision-support.v1"

_CORE_DECISION_PAYLOAD_FIELDS = (
    "suitability",
    "gate_decision",
    "proposal_decision_summary",
    "proposal_alternatives",
    "drift_analysis",
)


class CoreDecisionCompatibilitySnapshot(BaseModel):
    """Non-authoritative Core decision output retained only for migration parity evidence."""

    model_config = ConfigDict(extra="forbid")

    reported_status: str | None = None
    suitability: dict[str, Any] | None = None
    gate_decision: dict[str, Any] | None = None
    proposal_decision_summary: dict[str, Any] | None = None
    proposal_alternatives: dict[str, Any] | None = None
    drift_analysis: dict[str, Any] | None = None

    def has_core_decision_payload(self) -> bool:
        return any(
            value is not None
            for value in (
                self.suitability,
                self.gate_decision,
                self.proposal_decision_summary,
                self.proposal_alternatives,
                self.drift_analysis,
            )
        )


class CoreProjectedTransactionEffects(BaseModel):
    """Core-owned transaction effects consumed by Advise decision policy."""

    model_config = ConfigDict(extra="forbid")

    proposal_run_id: str
    correlation_id: str
    core_reported_status: Literal["READY", "BLOCKED", "PENDING_REVIEW"]
    before: SimulatedState
    intents: list[Annotated[ProposalOrderIntent, Field(discriminator="intent_type")]]
    after_simulated: SimulatedState
    reconciliation: Reconciliation | None = None
    rule_results: list[RuleResult] = Field(default_factory=list)
    explanation: dict[str, Any]
    diagnostics: DiagnosticsData
    allocation_lens: ProposalAllocationLens = Field(default_factory=ProposalAllocationLens)
    lineage: LineageData


def map_core_payload_to_projected_transaction_effects(
    payload: dict[str, Any],
) -> CoreProjectedTransactionEffects:
    source_effect_payload = {
        key: deepcopy(value)
        for key, value in payload.items()
        if key not in (*_CORE_DECISION_PAYLOAD_FIELDS, "status")
    }
    source_effect_payload["core_reported_status"] = payload.get("status")
    return cast(
        CoreProjectedTransactionEffects,
        CoreProjectedTransactionEffects.model_validate(source_effect_payload),
    )


def extract_core_decision_compatibility_snapshot(
    payload: dict[str, Any],
) -> CoreDecisionCompatibilitySnapshot:
    return CoreDecisionCompatibilitySnapshot(
        reported_status=payload.get("status") if isinstance(payload.get("status"), str) else None,
        suitability=_dict_or_none(payload.get("suitability")),
        gate_decision=_dict_or_none(payload.get("gate_decision")),
        proposal_decision_summary=_dict_or_none(payload.get("proposal_decision_summary")),
        proposal_alternatives=_dict_or_none(payload.get("proposal_alternatives")),
        drift_analysis=_dict_or_none(payload.get("drift_analysis")),
    )


def build_advise_owned_proposal_result_from_source_effects(
    *,
    request: ProposalSimulateRequest,
    source_effects: CoreProjectedTransactionEffects,
    compatibility_snapshot: CoreDecisionCompatibilitySnapshot,
    policy_context: dict[str, object] | None,
) -> ProposalResult:
    result_status = _advise_status_from_source_effects(source_effects)
    explanation = _advise_source_effect_explanation(
        source_effects=source_effects,
        compatibility_snapshot=compatibility_snapshot,
    )
    decision_support = build_simulation_decision_support(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        shelf=request.shelf_entries,
        options=request.options,
        diagnostics=source_effects.diagnostics,
        before=source_effects.before,
        after=source_effects.after_simulated,
        intent_plan=_intent_plan_from_source_effects(
            request=request,
            source_effects=source_effects,
        ),
        final_status=result_status,
        rule_results=source_effects.rule_results,
        reference_model=request.reference_model,
        policy_context=policy_context,
    )

    return ProposalResult(
        proposal_run_id=source_effects.proposal_run_id,
        correlation_id=source_effects.correlation_id,
        status=result_status,
        before=source_effects.before,
        intents=source_effects.intents,
        after_simulated=source_effects.after_simulated,
        reconciliation=source_effects.reconciliation,
        rule_results=source_effects.rule_results,
        explanation=explanation,
        diagnostics=source_effects.diagnostics,
        drift_analysis=decision_support.drift_analysis,
        suitability=decision_support.suitability,
        gate_decision=decision_support.gate_decision,
        allocation_lens=source_effects.allocation_lens,
        lineage=source_effects.lineage,
    )


def _advise_status_from_source_effects(
    source_effects: CoreProjectedTransactionEffects,
) -> Literal["READY", "BLOCKED", "PENDING_REVIEW"]:
    if (
        source_effects.reconciliation is not None
        and source_effects.reconciliation.status == "MISMATCH"
    ):
        return "BLOCKED"
    return cast(
        Literal["READY", "BLOCKED", "PENDING_REVIEW"],
        derive_status_from_rules(source_effects.rule_results),
    )


def _intent_plan_from_source_effects(
    *,
    request: ProposalSimulateRequest,
    source_effects: CoreProjectedTransactionEffects,
) -> SimulationIntentPlan:
    return SimulationIntentPlan(
        after_portfolio=request.portfolio_snapshot,
        cash_flows=[ProposedCashFlow.model_validate(item) for item in request.proposed_cash_flows],
        trades=[ProposedTrade.model_validate(item) for item in request.proposed_trades],
        intents=list(source_effects.intents),
        hard_failures=[],
        force_pending_review=False,
    )


def _advise_source_effect_explanation(
    *,
    source_effects: CoreProjectedTransactionEffects,
    compatibility_snapshot: CoreDecisionCompatibilitySnapshot,
) -> dict[str, Any]:
    explanation = deepcopy(source_effects.explanation)
    explanation["core_projected_transaction_effects"] = {
        "source_service": "lotus-core",
        "contract_version": source_effects.lineage.simulation_contract_version,
        "source_effects_hash": hash_canonical_payload(_source_effect_hash_payload(source_effects)),
        "request_hash": source_effects.lineage.request_hash,
        "portfolio_snapshot_id": source_effects.lineage.portfolio_snapshot_id,
        "market_data_snapshot_id": source_effects.lineage.market_data_snapshot_id,
        "core_reported_status": source_effects.core_reported_status,
        "core_reported_status_authoritative": False,
        "advise_calculation_version": ADVISE_DECISION_CALCULATION_VERSION,
    }
    if compatibility_snapshot.has_core_decision_payload():
        explanation["non_authoritative_core_decisions"] = compatibility_snapshot.model_dump(
            mode="json",
            exclude_none=True,
        )
    return explanation


def _source_effect_hash_payload(
    source_effects: CoreProjectedTransactionEffects,
) -> dict[str, Any]:
    payload = cast(dict[str, Any], source_effects.model_dump(mode="json", by_alias=False))
    payload.pop("core_reported_status", None)
    return payload


def _dict_or_none(value: object) -> dict[str, Any] | None:
    return cast(dict[str, Any], deepcopy(value)) if isinstance(value, dict) else None


__all__ = [
    "ADVISE_DECISION_CALCULATION_VERSION",
    "CoreDecisionCompatibilitySnapshot",
    "CoreProjectedTransactionEffects",
    "build_advise_owned_proposal_result_from_source_effects",
    "extract_core_decision_compatibility_snapshot",
    "map_core_payload_to_projected_transaction_effects",
]
