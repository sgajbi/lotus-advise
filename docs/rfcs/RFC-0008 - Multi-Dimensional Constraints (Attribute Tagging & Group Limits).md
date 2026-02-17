
# RFC-0008: Multi-Dimensional Constraints (Attribute Tagging & Group Limits)

**Status:** DRAFT
**Created:** 2026-02-17
**Depends On:** RFC-0007A (Contract Tightening)

---

## 0. Executive Summary

This RFC expands the engine's constraint capabilities beyond simple "Single Position" limits. It introduces a generic **Attribute Tagging** system for assets and a **Group Constraint** logic layer.

**Key Capabilities:**
1.  **Tagging:** Assets in the shelf can be tagged with metadata (e.g., `sector: "TECH"`, `region: "EM"`, `esg: "AAA"`).
2.  **Group Limits:** The engine can enforce maximum weight limits on any tag group (e.g., "Max 20% in TECH").
3.  **Redistribution:** Excess weight from a breached group is automatically redistributed to eligible assets outside that group.

---

## 1. Problem Statement

Currently, the engine only supports:
* `single_position_max_weight` (e.g., "No single stock > 10%").
* `cash_band` (e.g., "Cash between 2% and 5%").

**The Gap:**
Wealth mandates often require broader diversification rules. Example:
> "Construct a portfolio, but ensure **Technology** sector exposure does not exceed **20%**, and **Emerging Markets** exposure does not exceed **15%**."

Without this, the engine might satisfy the *single* position limit (e.g., owning 10 tech stocks at 5% each) while violating the *sector* risk tolerance (50% total Tech exposure).

---

## 2. Goals

### 2.1 Functional Requirements
* **Schema Update:** Allow `ShelfEntry` to carry arbitrary key-value tags.
* **Configuration:** Allow `EngineOptions` to define limits for specific tags.
* **Logic:**
    * In **Stage 3 (Target Generation)**, calculate total weight per tag.
    * If a limit is breached (e.g., Tech = 25% > 20%), cap the contributing assets proportionally.
    * Redistribute the 5% excess to non-Tech assets.
* **Reporting:** Output the final allocation by these tags in the `after_simulated` state.

---

## 3. Proposed Implementation

### 3.1 Data Model Changes (`src/core/models.py`)

**1. Update `ShelfEntry`**
Add a dictionary for flexible attributes.

```python
class ShelfEntry(BaseModel):
    instrument_id: str
    status: Literal["APPROVED", "RESTRICTED", "BANNED", "SUSPENDED", "SELL_ONLY"]
    asset_class: str = "UNKNOWN"
    min_notional: Optional[Money] = None
    # NEW: Generic attributes
    attributes: Dict[str, str] = Field(default_factory=dict) 

```

**2. Update `EngineOptions**`
Define the constraint structure.

```python
class GroupConstraint(BaseModel):
    max_weight: Decimal

class EngineOptions(BaseModel):
    # ... existing fields ...
    
    # NEW: Key is "attribute_name:attribute_value", e.g., "sector:TECH"
    group_constraints: Dict[str, GroupConstraint] = Field(default_factory=dict)

```

### 3.2 Logic Changes (`src/core/engine.py`)

**Modify `_generate_targets` (Stage 3):**

The engine currently loops to apply `single_position_max_weight`. We will inject a **Group Constraint Loop** *before* the single position check.

**Algorithm:**

1. **Identify Groups:** Iterate through `options.group_constraints`.
2. **Calculate Current Weight:** Sum the weights of all `eligible_targets` that match the group (e.g., `shelf.attributes['sector'] == 'TECH'`).
3. **Check Breach:** If `Sum > Max_Weight`:
* Calculate `Scaling_Factor = Max_Weight / Sum`.
* Multiply the weight of every asset in that group by `Scaling_Factor`.
* Add the removed weight to `excess_pool`.


4. **Redistribute:** Distribute `excess_pool` to assets *not* in the constrained group.

### 3.3 Output Enhancements (`src/core/valuation.py`)

Update `build_simulated_state` to generate an `allocation_by_attribute` report, so the user can verify the results.

```python
# In SimulatedState
allocation_by_attribute: Dict[str, List[AllocationMetric]] 
# Example: {"sector": [...], "region": [...]}

```

---

## 4. Test Plan (Golden Scenarios)

We will create a new Golden Scenario: `tests/golden_data/scenario_08_sector_cap.json`.

**Scenario:**

* **Portfolio:** 100% Cash.
* **Model:**
* `Tech_Stock_A`: 15%
* `Tech_Stock_B`: 15%
* `Bond_Fund_C`: 70%


* **Shelf:**
* A & B have `attributes: {"sector": "TECH"}`.


* **Options:**
* `group_constraints`: `{"sector:TECH": {"max_weight": 0.20}}`.



**Expected Outcome:**

* Tech A & B are capped at **10% each** (Total 20%).
* Bond C absorbs the excess, rising to **80%**.
* **Status:** `READY`.
* **Trace:** Tags `CAPPED_BY_GROUP_LIMIT` appear on A & B.

---

## 5. Future Considerations

* **Min Weight:** Future support for "At least 10% in ESG".
* **Intersection:** Handling assets that belong to multiple constrained groups (e.g., "Tech" AND "China"). For this MVP, we will apply constraints sequentially.

```

```