# RFC-0012: Mathematical Optimization (Solver Integration)

**Status:** DRAFT
**Created:** 2026-02-17
**Depends On:** RFC-0008 (Multi-Dimensional Constraints)

---

## 0. Executive Summary

This RFC proposes replacing the heuristic "waterfall" logic in Stage 3 (Target Generation) with a deterministic **Convex Optimization Solver** (using `cvxpy`).

**Key Capabilities:**
1.  **Global Optimization:** Instead of fixing constraints one by one (which can break previous fixes), the solver finds a solution that satisfies *all* constraints simultaneously.
2.  **Objective Function:** Minimizes Tracking Error (distance from Model) while strictly obeying Hard Constraints.
3.  **Infeasibility Detection:** Mathematically proves if a request is impossible (e.g., "Min Cash 10%" + "Max Cash 5%") and returns a precise error.

---

## 1. Problem Statement

Currently, the engine uses iterative logic (`while` loops) to satisfy constraints:
1.  Fix `SELL_ONLY` assets.
2.  Then, fix `single_position_max_weight`.
3.  Then, fix `cash_band`.

**The Flaw:**
* Fixing the **Cash Band** might force buying more assets, which could breach the **Single Position Limit** you just fixed.
* As we add more constraints (RFC-0008 Sectors, RFC-0009 Tax), this "Whack-a-Mole" approach becomes unmaintainable and prone to infinite loops or suboptimal results.

---

## 2. Goals

### 2.1 Functional Requirements
* **Library:** Introduce `cvxpy` (or `scipy.optimize`) as a core dependency.
* **Logic (Stage 3 Replacement):**
    * Construct a weight vector variable $w$.
    * **Objective:** Minimize $||w - w_{model}||^2$ (Least Squares).
    * **Constraints:**
        * $\sum w = 1$ (Fully Invested).
        * $w_i \ge 0$ (No Shorting).
        * $w_{cash} \ge Min_{cash}$.
        * $w_{sector\_tech} \le 0.20$.
* **Fallback:** If the solver fails (Infeasible), return `BLOCKED` with specific conflict details.

---

## 3. Proposed Implementation

### 3.1 Dependencies
Add to `requirements.txt`:
```text
cvxpy>=1.4.0
numpy>=1.26.0

```

### 3.2 Logic Changes (`src/core/engine.py`)

**Replace `_generate_targets` with `_solve_targets`:**

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

### 3.3 Performance Note

For portfolios < 1000 assets, `cvxpy` solves in milliseconds. This is comparable to the current Python loops but significantly more robust.

---

## 4. Test Plan (Golden Scenarios)

We will create `tests/golden_data/scenario_12_solver_conflict.json`.

**Scenario:**

* **Model:** 100% in `Tech_Stock_A`.
* **Constraints:**
* `single_position_max`: 40%.
* `sector:TECH max`: 30%.
* `min_cash`: 50%.



**Logic Check:**

* **Iterative Approach:** Might loop forever or crash trying to satisfy all three.
* **Solver Approach:**
* Must have 50% Cash. Remaining space: 50%.
* Tech Max is 30%. So `Tech_Stock_A` gets 30%.
* Remaining 20%? If no other assets exist in the universe, it's **Infeasible**.
* If a `Bond_Fund` exists, it allocates 20% there to satisfy .



**Expected Outcome:**

* **Status:** `READY` (if valid filler exists) or `BLOCKED` (if mathematically impossible).
* **Allocation:**
* Cash: 50% (Constraint active)
* Tech A: 30% (Group Constraint active)
* Bond B: 20% (Gap filler)



```

```