"""
FILE: src/core/compliance.py
Post-trade Rule Engine implementation (RFC-0005).
"""

from decimal import Decimal
from typing import List

from src.core.models import EngineOptions, RuleResult, SimulatedState


class RuleEngine:
    """
    Evaluates business rules against the simulated after-state.
    Supports HARD (Block), SOFT (Review), and INFO (Log) severities.
    """

    @staticmethod
    def evaluate(state: SimulatedState, options: EngineOptions) -> List[RuleResult]:
        results = []

        # 1. CASH_BAND (Soft)
        # Checks if total cash weight exceeds policy max (default 5%)
        cash_weight = next(
            (a.weight for a in state.allocation_by_asset_class if a.key == "CASH"), Decimal("0")
        )
        # In a real app, threshold comes from Policy/Options. Hardcoded 5% for MVP as per spec.
        cash_max = Decimal("0.05")
        if cash_weight > cash_max:
            results.append(
                RuleResult(
                    rule_id="CASH_BAND",
                    severity="SOFT",
                    status="FAIL",
                    measured=cash_weight,
                    threshold={"max": cash_max},
                    reason_code="THRESHOLD_BREACH",
                    remediation_hint="Portfolio has excess cash. Consider investing or verifying exclusions.",
                )
            )
        else:
            results.append(
                RuleResult(
                    rule_id="CASH_BAND",
                    severity="SOFT",
                    status="PASS",
                    measured=cash_weight,
                    threshold={"max": cash_max},
                    reason_code="OK",
                )
            )

        # 2. SINGLE_POSITION_MAX (Hard)
        # Checks if any single instrument exceeds the max weight (post-simulation)
        # This catches drift that might happen due to rounding or FX moves after the target phase.
        if options.single_position_max_weight:
            max_w = options.single_position_max_weight
            for pos in state.allocation_by_instrument:
                if pos.weight > max_w + Decimal("0.001"):  # Small tolerance for rounding
                    results.append(
                        RuleResult(
                            rule_id="SINGLE_POSITION_MAX",
                            severity="HARD",
                            status="FAIL",
                            measured=pos.weight,
                            threshold={"max": max_w},
                            reason_code="LIMIT_BREACH",
                            remediation_hint=f"Instrument {pos.key} exceeds max weight of {max_w}",
                        )
                    )

        # 3. RECONCILIATION (Hard) - RFC-0005 Requirement
        # (This is typically handled in the Engine, but can be a rule here if we pass before_state)
        # For now, we focus on portfolio composition rules.

        return results
