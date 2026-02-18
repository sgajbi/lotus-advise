from decimal import Decimal

from src.core.models import Money, TargetInstrument


def _collect_infeasibility_hints(*, tradeable_ids, locked_weight, options, eligible_targets, shelf):
    hints = []

    invested_min = Decimal("1.0") - options.cash_band_max_weight - locked_weight
    invested_max = Decimal("1.0") - options.cash_band_min_weight - locked_weight
    if invested_min > invested_max:
        hints.append("INFEASIBILITY_HINT_CASH_BAND_CONTRADICTION")

    if options.single_position_max_weight is not None:
        max_capacity = options.single_position_max_weight * Decimal(len(tradeable_ids))
        if max_capacity < invested_min:
            hints.append("INFEASIBILITY_HINT_SINGLE_POSITION_CAPACITY")

    indexed_tradeable = {i_id: idx for idx, i_id in enumerate(tradeable_ids)}
    for constraint_key in sorted(options.group_constraints.keys()):
        constraint = options.group_constraints[constraint_key]
        attr_key, attr_val = constraint_key.split(":", 1)
        group_locked_weight = Decimal("0")
        group_tradeable_count = 0
        for i_id in eligible_targets:
            s_ent = next((s for s in shelf if s.instrument_id == i_id), None)
            if not s_ent or s_ent.attributes.get(attr_key) != attr_val:
                continue
            if i_id in indexed_tradeable:
                group_tradeable_count += 1
            else:
                group_locked_weight += eligible_targets[i_id]

        if group_locked_weight > constraint.max_weight:
            hints.append(f"INFEASIBILITY_HINT_LOCKED_GROUP_WEIGHT_{constraint_key}")
        if group_tradeable_count == 0 and group_locked_weight == Decimal("0"):
            continue

    return hints


def build_target_trace(model, eligible_targets, buy_list, total_val, base_ccy):
    trace = []
    for t in model.targets:
        final_w = eligible_targets.get(t.instrument_id, Decimal("0.0"))
        tags = ["CAPPED_BY_MAX_WEIGHT"] if t.weight > final_w else []

        if final_w > t.weight:
            tags.append("REDISTRIBUTED_RECIPIENT")
        trace.append(
            TargetInstrument(
                instrument_id=t.instrument_id,
                model_weight=t.weight,
                final_weight=final_w,
                final_value=Money(amount=total_val * final_w, currency=base_ccy),
                tags=tags,
            )
        )

    for i_id, final_w in eligible_targets.items():
        if not any(t.instrument_id == i_id for t in model.targets):
            tag = (
                "IMPLICIT_SELL_TO_ZERO" if (i_id in buy_list or final_w == 0) else "LOCKED_POSITION"
            )
            trace.append(
                TargetInstrument(
                    instrument_id=i_id,
                    model_weight=Decimal("0.0"),
                    final_weight=final_w,
                    final_value=Money(amount=total_val * final_w, currency=base_ccy),
                    tags=[tag],
                )
            )

    return trace


def generate_targets_solver(
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
    try:
        import cvxpy as cp
        import numpy as np
    except ImportError:
        diagnostics.warnings.append("SOLVER_ERROR")
        return [], "BLOCKED"

    status = "READY"
    if sell_only_excess > Decimal("0.0"):
        recs = {k: v for k, v in eligible_targets.items() if k in buy_list}
        total_rec = sum(recs.values())
        if total_rec > Decimal("0.0"):
            for i_id, w in recs.items():
                eligible_targets[i_id] = w + (sell_only_excess * (w / total_rec))
        else:
            status = "PENDING_REVIEW"

    tradeable_ids = [i_id for i_id in eligible_targets if i_id in buy_list]
    locked_ids = [i_id for i_id in eligible_targets if i_id not in buy_list]
    locked_weight = sum(eligible_targets[i_id] for i_id in locked_ids)

    if not tradeable_ids:
        return build_target_trace(model, eligible_targets, buy_list, total_val, base_ccy), status

    model_weights = {t.instrument_id: t.weight for t in model.targets}
    w_model = np.array([float(model_weights.get(i_id, Decimal("0.0"))) for i_id in tradeable_ids])
    w = cp.Variable(len(tradeable_ids))

    objective = cp.Minimize(cp.sum_squares(w - w_model))
    constraints = [w >= 0]

    invested_min = Decimal("1.0") - options.cash_band_max_weight - locked_weight
    invested_max = Decimal("1.0") - options.cash_band_min_weight - locked_weight
    constraints.append(cp.sum(w) >= float(invested_min))
    constraints.append(cp.sum(w) <= float(invested_max))

    if options.single_position_max_weight is not None:
        constraints.append(w <= float(options.single_position_max_weight))

    indexed_tradeable = {i_id: idx for idx, i_id in enumerate(tradeable_ids)}
    sorted_keys = sorted(options.group_constraints.keys())
    for constraint_key in sorted_keys:
        constraint = options.group_constraints[constraint_key]
        attr_key, attr_val = constraint_key.split(":", 1)

        if not any(attr_key in s.attributes for s in shelf):
            diagnostics.warnings.append(f"UNKNOWN_CONSTRAINT_ATTRIBUTE_{attr_key}")
            continue

        group_tradeable = []
        group_locked_weight = Decimal("0")
        for i_id in eligible_targets:
            s_ent = next((s for s in shelf if s.instrument_id == i_id), None)
            if not s_ent or s_ent.attributes.get(attr_key) != attr_val:
                continue
            if i_id in indexed_tradeable:
                group_tradeable.append(i_id)
            else:
                group_locked_weight += eligible_targets[i_id]

        if not group_tradeable and group_locked_weight == Decimal("0"):
            continue

        group_expr = cp.sum([w[indexed_tradeable[i_id]] for i_id in group_tradeable]) + float(
            group_locked_weight
        )
        constraints.append(group_expr <= float(constraint.max_weight))

    prob = cp.Problem(objective, constraints)
    solved = False
    latest_status = None
    for solver_name in (cp.OSQP, cp.SCS):
        try:
            prob.solve(solver=solver_name, verbose=False, warm_start=False)
        except cp.SolverError:
            continue
        latest_status = str(prob.status).upper()
        if prob.status in ("optimal", "optimal_inaccurate"):
            solved = True
            break

    if not solved:
        reason = "SOLVER_ERROR" if latest_status is None else f"INFEASIBLE_{latest_status}"
        diagnostics.warnings.append(reason)
        if reason.startswith("INFEASIBLE_"):
            diagnostics.warnings.extend(
                _collect_infeasibility_hints(
                    tradeable_ids=tradeable_ids,
                    locked_weight=locked_weight,
                    options=options,
                    eligible_targets=eligible_targets,
                    shelf=shelf,
                )
            )
        return [], "BLOCKED"

    for idx, i_id in enumerate(tradeable_ids):
        solved_weight = Decimal(str(max(float(w.value[idx]), 0.0))).quantize(Decimal("0.0001"))
        eligible_targets[i_id] = solved_weight

    return build_target_trace(model, eligible_targets, buy_list, total_val, base_ccy), status
