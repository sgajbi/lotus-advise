from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, cast

from src.core.advisory.intents import expected_cash_delta_base
from src.core.advisory.simulation_intent_plan import SimulationIntentPlan
from src.core.common.simulation_shared import build_reconciliation, derive_status_from_rules
from src.core.compliance import RuleEngine
from src.core.diagnostics_models import DiagnosticsData, RuleResult
from src.core.engine_options_models import EngineOptions
from src.core.portfolio_models import MarketDataSnapshot, PortfolioSnapshot
from src.core.proposal_effect_models import Reconciliation
from src.core.simulation_state_models import SimulatedState


@dataclass(frozen=True)
class SimulationReview:
    final_status: Literal["READY", "BLOCKED", "PENDING_REVIEW"]
    rule_results: list[RuleResult]
    reconciliation: Reconciliation


def evaluate_simulation_review(
    *,
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    options: EngineOptions,
    diagnostics: DiagnosticsData,
    before: SimulatedState,
    after: SimulatedState,
    intent_plan: SimulationIntentPlan,
) -> SimulationReview:
    rule_results = RuleEngine.evaluate(after, options, diagnostics)

    _append_input_guard_failure_if_needed(rule_results, intent_plan)
    _append_funding_data_quality_failure_if_needed(rule_results, diagnostics, intent_plan)

    final_status = derive_status_from_rules(rule_results)
    reconciliation, recon_diff, tolerance = _build_value_reconciliation(
        portfolio=portfolio,
        market_data=market_data,
        before=before,
        after=after,
        intent_plan=intent_plan,
        diagnostics=diagnostics,
    )

    final_status = _final_status_after_reconciliation(
        final_status=final_status,
        rule_results=rule_results,
        reconciliation=reconciliation,
        recon_diff=recon_diff,
        tolerance=tolerance,
    )
    final_status = _final_status_after_pending_review(
        final_status=final_status,
        intent_plan=intent_plan,
    )

    return SimulationReview(
        final_status=final_status,
        rule_results=rule_results,
        reconciliation=reconciliation,
    )


def _append_input_guard_failure_if_needed(
    rule_results: list[RuleResult],
    intent_plan: SimulationIntentPlan,
) -> None:
    if not intent_plan.hard_failures:
        return
    rule_results.append(
        RuleResult(
            rule_id="PROPOSAL_INPUT_GUARDS",
            severity="HARD",
            status="FAIL",
            measured=Decimal(len(intent_plan.hard_failures)),
            threshold={"max": Decimal("0")},
            reason_code=intent_plan.hard_failures[0],
            remediation_hint=("Adjust proposal cash flows, funding inputs, or shelf eligibility."),
        )
    )


def _append_funding_data_quality_failure_if_needed(
    rule_results: list[RuleResult],
    diagnostics: DiagnosticsData,
    intent_plan: SimulationIntentPlan,
) -> None:
    if not intent_plan.force_pending_review:
        return
    rule_results.append(
        RuleResult(
            rule_id="PROPOSAL_FUNDING_DQ",
            severity="SOFT",
            status="FAIL",
            measured=Decimal(len(diagnostics.missing_fx_pairs)),
            threshold={"max": Decimal("0")},
            reason_code="MISSING_FX_FOR_FUNDING",
            remediation_hint="Provide required FX rates for advisory auto-funding.",
        )
    )


def _final_status_after_reconciliation(
    *,
    final_status: Literal["READY", "BLOCKED", "PENDING_REVIEW"],
    rule_results: list[RuleResult],
    reconciliation: Reconciliation,
    recon_diff: Decimal,
    tolerance: Decimal,
) -> Literal["READY", "BLOCKED", "PENDING_REVIEW"]:
    if reconciliation.status != "MISMATCH":
        return final_status
    rule_results.append(
        RuleResult(
            rule_id="RECONCILIATION",
            severity="HARD",
            status="FAIL",
            measured=recon_diff,
            threshold={"max": tolerance},
            reason_code="VALUE_MISMATCH",
            remediation_hint="Check pricing/FX or proposal inputs.",
        )
    )
    return "BLOCKED"


def _final_status_after_pending_review(
    *,
    final_status: Literal["READY", "BLOCKED", "PENDING_REVIEW"],
    intent_plan: SimulationIntentPlan,
) -> Literal["READY", "BLOCKED", "PENDING_REVIEW"]:
    if intent_plan.force_pending_review and final_status == "READY":
        return "PENDING_REVIEW"
    return final_status


def _build_value_reconciliation(
    *,
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    before: SimulatedState,
    after: SimulatedState,
    intent_plan: SimulationIntentPlan,
    diagnostics: DiagnosticsData,
) -> tuple[Reconciliation, Decimal, Decimal]:
    expected_delta_base = expected_cash_delta_base(
        portfolio=portfolio,
        market_data=market_data,
        cash_flows=intent_plan.cash_flows,
        dq_log=diagnostics.data_quality,
    )
    expected_after_total = before.total_value.amount + expected_delta_base
    return cast(
        tuple[Reconciliation, Decimal, Decimal],
        build_reconciliation(
            before_total=before.total_value.amount,
            after_total=after.total_value.amount,
            expected_after_total=expected_after_total,
            base_currency=portfolio.base_currency,
            use_absolute_scale=True,
        ),
    )
