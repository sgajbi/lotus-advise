# RFC-0012: Mathematical Optimization (Solver Integration)

| Metadata | Details |
| --- | --- |
| **Status** | DRAFT |
| **Created** | 2026-02-17 |
| **Target Release** | TBD |
| **Doc Location** | docs/rfcs/RFC-0012-mathematical-optimization-solver-integration.md |

---

## 0. Executive Summary

This RFC replaces iterative Stage 3 target heuristics with a convex optimization problem solved by `cvxpy`.

Key outcomes:
1. Enforce all hard constraints in one solve.
2. Minimize tracking error versus model weights.
3. Return explicit infeasibility diagnostics when no feasible solution exists.

---

## 1. Problem Statement

Sequential fix-up loops are fragile when constraints interact. Later corrections can violate earlier ones, and behavior becomes sensitive to rule ordering. With expanding constraint sets, this approach is difficult to reason about and test.

---

## 2. Goals and Non-Goals

### 2.1 Goals
1. Introduce a solver-backed target engine for Stage 3.
2. Keep constraints explicit, auditable, and testable.
3. Provide deterministic outputs for same inputs and solver settings.
4. Return structured failure diagnostics for infeasible requests.

### 2.2 Non-Goals
1. Mixed-integer optimization for lot-size, minimum tickets, or cardinality.
2. Replacing Stages 4 and 5 in this RFC.
3. Tax-budget and settlement-time optimization in objective.

---

## 3. Proposed Implementation

### 3.1 Dependencies

Add:

```text
cvxpy>=1.4.0
numpy>=1.26.0
```

### 3.2 Target Solver (`src/core/engine.py`)

Replace target generation with `_solve_targets`.

```python
import cvxpy as cp
import numpy as np

def _solve_targets(model, universe, options, current_valuations):
    # 1. Setup Variables
    n = len(universe.all_instruments)
    w = cp.Variable(n)
    w_model = np.array([model.get_weight(i) for i in universe.all_instruments])
    
    # 2. Define Objective: Minimize distance to Model Weights
    objective = cp.Minimize(cp.sum_squares(w - w_model))
    
    # 3. Define Constraints
    constraints = [
        cp.sum(w) == 1,         # Budget Constraint
        w >= 0,                 # No Shorting (in target weights)
    ]
    
    # Position Limits
    if options.single_position_max_weight:
        constraints.append(w <= options.single_position_max_weight)
        
    # Group Limits (RFC-0008)
    for group, limit in options.group_constraints.items():
        indices = universe.get_indices_for_group(group)
        constraints.append(cp.sum(w[indices]) <= limit.max_weight)
        
    # Cash band lower/upper if configured
    # Example: cash index set C
    # constraints.append(cp.sum(w[C]) >= options.cash_band.min)
    # constraints.append(cp.sum(w[C]) <= options.cash_band.max)

    # 4. Solve
    prob = cp.Problem(objective, constraints)
    try:
        prob.solve()
    except cp.SolverError:
        return "BLOCKED", "SOLVER_ERROR"
        
    if prob.status not in ["optimal", "optimal_inaccurate"]:
        return "BLOCKED", f"INFEASIBLE_{prob.status.upper()}"
        
    # 5. Extract Result
    final_weights = w.value
    # ... map back to instrument_ids ...
    return final_weights

```

Implementation requirements:
1. Use a fixed solver preference order (for example `OSQP` then `SCS`) for deterministic behavior.
2. Capture dual infeasibility details when available and map to diagnostics.
3. Keep legacy heuristic as feature-flag fallback during rollout (`options.target_method`).

### 3.3 Objective and Constraints

Baseline objective:
1. Minimize squared distance from model weights.

Hard constraints:
1. Full investment: `sum(w) == 1`.
2. Long-only: `w >= 0` unless shorting explicitly enabled.
3. Single-name max.
4. Group max (RFC-0008).
5. Cash band min/max.

Soft constraints (future extension):
1. Turnover penalty term.
2. Cost-aware penalty term.

---

## 4. Test Plan

Add `tests/golden_data/scenario_12_solver_conflict.json`.

Scenario A (feasible):
1. Model 100% `Tech_A`.
2. Constraints: single-name max 40%, `sector:TECH <= 30%`, `cash >= 50%`.
3. Universe includes `Bond_B`.

Expected:
1. `cash=50%`, `Tech_A=30%`, `Bond_B=20%`.
2. Status `READY`.

Scenario B (infeasible):
1. Same constraints but no non-tech filler instrument.

Expected:
1. Status `BLOCKED`.
2. Diagnostic reason indicates infeasibility class.

---

## 5. Rollout and Compatibility

1. Add feature flag: `target_method = HEURISTIC | SOLVER`.
2. Run dual-path comparison in CI on golden scenarios before default switch.
3. Keep heuristic fallback for one release cycle.

### 5.1 Carry-Forward Requirements from RFC-0001 to RFC-0007A

1. Canonical simulate endpoint remains `POST /rebalance/simulate`.
2. Solver integration must preserve current status contract (`READY`, `PENDING_REVIEW`, `BLOCKED`) and existing safety blocks.
3. Universe eligibility already includes all non-zero held positions (`qty != 0`); solver rollout must preserve this behavior.
4. RFC-0008 group-constraint semantics are already implemented and must be preserved in solver constraints.
5. Do not assume persistence-backed idempotency store; reproducibility remains input-deterministic within stateless execution.

---

## 6. Open Questions

1. Which solver backend should be production default for stability and speed?
2. Do we require strict reproducibility across OS/architecture in acceptance tests?

---

## 7. Status and Reason Code Conventions

1. Run status values remain aligned to RFC-0007A: `READY`, `PENDING_REVIEW`, `BLOCKED`.
2. Solver failures and infeasibility must be represented as diagnostics reason codes in upper snake case.
3. This RFC introduces reason code patterns:
   1. `SOLVER_ERROR`
   2. `INFEASIBLE_<SOLVER_STATUS>`
