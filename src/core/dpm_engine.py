"""
FILE: src/core/dpm_engine.py
"""

import uuid
from copy import deepcopy
from decimal import Decimal

from src.core.common.diagnostics import make_diagnostics_data
from src.core.common.workflow_gates import evaluate_gate_decision
from src.core.compliance import RuleEngine
from src.core.dpm.execution import (
    build_settlement_ladder as build_settlement_ladder_impl,
)
from src.core.dpm.execution import (
    check_blocking_dq as check_blocking_dq_impl,
)
from src.core.dpm.execution import (
    generate_fx_and_simulate as generate_fx_and_simulate_impl,
)
from src.core.dpm.intents import generate_intents as generate_intents_impl
from src.core.dpm.targets import (
    apply_group_constraints as apply_group_constraints_impl,
)
from src.core.dpm.targets import (
    compare_target_generation_methods as compare_target_generation_methods_impl,
)
from src.core.dpm.targets import (
    generate_targets as generate_targets_impl,
)
from src.core.dpm.targets import (
    generate_targets_heuristic as generate_targets_heuristic_impl,
)
from src.core.dpm.turnover import (
    apply_turnover_limit as apply_turnover_limit_impl,
)
from src.core.dpm.turnover import (
    calculate_turnover_score as calculate_turnover_score_impl,
)
from src.core.dpm.universe import build_universe as build_universe_impl
from src.core.models import (
    LineageData,
    RebalanceResult,
    TargetData,
    UniverseCoverage,
    UniverseData,
)
from src.core.valuation import build_simulated_state


def _calculate_turnover_score(intent, portfolio_value_base):
    return calculate_turnover_score_impl(intent, portfolio_value_base)


def _apply_turnover_limit(
    intents,
    options,
    portfolio_value_base,
    base_currency,
    diagnostics,
):
    return apply_turnover_limit_impl(
        intents=intents,
        options=options,
        portfolio_value_base=portfolio_value_base,
        base_currency=base_currency,
        diagnostics=diagnostics,
    )


def _make_blocked_result(
    run_id,
    portfolio,
    before,
    buy_l,
    sell_l,
    excl,
    trace,
    options,
    diagnostics,
    request_hash,
):
    """Create a consistent blocked response payload."""
    rule_results = RuleEngine.evaluate(before, options, diagnostics)
    gate_decision = None
    if options.enable_workflow_gates:
        gate_decision = evaluate_gate_decision(
            status="BLOCKED",
            rule_results=rule_results,
            suitability=None,
            diagnostics=diagnostics,
            options=options,
            default_requires_client_consent=False,
        )
    return RebalanceResult(
        rebalance_run_id=run_id,
        correlation_id="c_none",
        status="BLOCKED",
        before=before,
        universe=UniverseData(
            universe_id=f"u_{run_id}",
            eligible_for_buy=buy_l,
            eligible_for_sell=sell_l,
            excluded=excl,
            coverage=UniverseCoverage(price_coverage_pct=0, fx_coverage_pct=0),
        ),
        target=TargetData(target_id=f"t_{run_id}", strategy={}, targets=trace),
        intents=[],
        after_simulated=before,
        rule_results=rule_results,
        diagnostics=diagnostics,
        gate_decision=gate_decision,
        explanation={"summary": "Blocked"},
        lineage=LineageData(
            portfolio_snapshot_id=portfolio.portfolio_id,
            market_data_snapshot_id="md",
            request_hash=request_hash,
        ),
    )


def _build_universe(model, portfolio, shelf, options, dq_log, current_val):
    return build_universe_impl(model, portfolio, shelf, options, dq_log, current_val)


def _apply_group_constraints(eligible_targets, buy_list, shelf, options, diagnostics):
    return apply_group_constraints_impl(eligible_targets, buy_list, shelf, options, diagnostics)


def _generate_targets(
    model,
    eligible_targets,
    buy_list,
    sell_only_excess,
    shelf=None,
    options=None,
    total_val=Decimal("0"),
    base_ccy="USD",
    diagnostics=None,
):
    return generate_targets_impl(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=buy_list,
        sell_only_excess=sell_only_excess,
        shelf=shelf,
        options=options,
        total_val=total_val,
        base_ccy=base_ccy,
        diagnostics=diagnostics,
    )


def _to_weight_map(trace):
    return {t.instrument_id: t.final_weight for t in trace}


def _compare_target_generation_methods(
    *,
    model,
    eligible_targets,
    buy_list,
    sell_only_excess,
    shelf,
    options,
    total_val,
    base_ccy,
    primary_trace,
    primary_status,
):
    return compare_target_generation_methods_impl(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=buy_list,
        sell_only_excess=sell_only_excess,
        shelf=shelf,
        options=options,
        total_val=total_val,
        base_ccy=base_ccy,
        primary_trace=primary_trace,
        primary_status=primary_status,
    )


def _generate_targets_heuristic(
    model,
    eligible_targets,
    buy_list,
    sell_only_excess,
    shelf,
    options,
    total_val,
    base_ccy,
    diagnostics,
):
    return generate_targets_heuristic_impl(
        model=model,
        eligible_targets=eligible_targets,
        buy_list=buy_list,
        sell_only_excess=sell_only_excess,
        shelf=shelf,
        options=options,
        total_val=total_val,
        base_ccy=base_ccy,
        diagnostics=diagnostics,
    )


def _generate_intents(
    portfolio, market_data, targets, shelf, options, total_val, dq_log, diagnostics, suppressed
):
    return generate_intents_impl(
        portfolio, market_data, targets, shelf, options, total_val, dq_log, diagnostics, suppressed
    )


def _build_settlement_ladder(portfolio, shelf, intents, options, diagnostics):
    return build_settlement_ladder_impl(portfolio, shelf, intents, options, diagnostics)


def _generate_fx_and_simulate(
    portfolio, market_data, shelf, intents, options, total_val_before, diagnostics
):
    return generate_fx_and_simulate_impl(
        portfolio, market_data, shelf, intents, options, total_val_before, diagnostics
    )


def _check_blocking_dq(dq_log, options):
    return check_blocking_dq_impl(dq_log, options)


def run_simulation(portfolio, market_data, model, shelf, options, request_hash="no_hash"):
    run_id = f"rr_{uuid.uuid4().hex[:8]}"
    diag_data = make_diagnostics_data()

    before = build_simulated_state(
        portfolio, market_data, shelf, diag_data.data_quality, diag_data.warnings, options
    )
    tv = before.total_value.amount

    eligible, excl, buy_l, sell_l, s_exc = _build_universe(
        model, portfolio, shelf, options, diag_data.data_quality, before
    )
    eligible_before_s3 = deepcopy(eligible)

    trace, s3_stat = _generate_targets(
        model, eligible, buy_l, s_exc, shelf, options, tv, portfolio.base_currency, diag_data
    )

    target_method_comparison = None
    if options.compare_target_methods:
        target_method_comparison = _compare_target_generation_methods(
            model=model,
            eligible_targets=eligible_before_s3,
            buy_list=buy_l,
            sell_only_excess=s_exc,
            shelf=shelf,
            options=options,
            total_val=tv,
            base_ccy=portfolio.base_currency,
            primary_trace=trace,
            primary_status=s3_stat,
        )
        primary_status = target_method_comparison["primary_status"]
        alternate_status = target_method_comparison["alternate_status"]
        if primary_status != alternate_status:
            diag_data.warnings.append("TARGET_METHOD_STATUS_DIVERGENCE")
        if target_method_comparison["differing_instruments"]:
            diag_data.warnings.append("TARGET_METHOD_WEIGHT_DIVERGENCE")

    if _check_blocking_dq(diag_data.data_quality, options) or s3_stat == "BLOCKED":
        return _make_blocked_result(
            run_id=run_id,
            portfolio=portfolio,
            before=before,
            buy_l=buy_l,
            sell_l=sell_l,
            excl=excl,
            trace=trace,
            options=options,
            diagnostics=diag_data,
            request_hash=request_hash,
        )

    intents, tax_impact = _generate_intents(
        portfolio,
        market_data,
        trace,
        shelf,
        options,
        tv,
        diag_data.data_quality,
        diag_data,
        diag_data.suppressed_intents,
    )

    if _check_blocking_dq(diag_data.data_quality, options):
        # Re-wrap diagnostics if DQ fails late (though typically caught earlier)
        return _make_blocked_result(
            run_id=run_id,
            portfolio=portfolio,
            before=before,
            buy_l=buy_l,
            sell_l=sell_l,
            excl=excl,
            trace=trace,
            options=options,
            diagnostics=diag_data,
            request_hash=request_hash,
        )

    intents = _apply_turnover_limit(
        intents=intents,
        options=options,
        portfolio_value_base=tv,
        base_currency=portfolio.base_currency,
        diagnostics=diag_data,
    )

    intents, after, rules, f_stat, recon = _generate_fx_and_simulate(
        portfolio, market_data, shelf, intents, options, tv, diag_data
    )

    if s3_stat == "PENDING_REVIEW" and f_stat == "READY":
        f_stat = "PENDING_REVIEW"
    gate_decision = None
    if options.enable_workflow_gates:
        gate_decision = evaluate_gate_decision(
            status=f_stat,
            rule_results=rules,
            suitability=None,
            diagnostics=diag_data,
            options=options,
            default_requires_client_consent=False,
        )

    return RebalanceResult(
        rebalance_run_id=run_id,
        correlation_id="c_none",
        status=f_stat,
        before=before,
        universe=UniverseData(
            universe_id=f"u_{run_id}",
            eligible_for_buy=buy_l,
            eligible_for_sell=sell_l,
            excluded=excl,
            coverage=UniverseCoverage(price_coverage_pct=1, fx_coverage_pct=1),
        ),
        target=TargetData(target_id=f"t_{run_id}", strategy={}, targets=trace),
        intents=intents,
        after_simulated=after,
        reconciliation=recon,
        tax_impact=tax_impact,
        rule_results=rules,
        diagnostics=diag_data,
        gate_decision=gate_decision,
        explanation={"summary": f_stat, "target_method_comparison": target_method_comparison},
        lineage=LineageData(
            portfolio_snapshot_id=portfolio.portfolio_id,
            market_data_snapshot_id="md",
            request_hash=request_hash,
        ),
    )
