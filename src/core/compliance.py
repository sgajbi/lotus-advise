"""
FILE: src/core/compliance.py
Post-trade Rule Engine implementation (RFC-0005).
"""

from decimal import Decimal
from typing import List

from src.core.models import DiagnosticsData, EngineOptions, RuleResult, SimulatedState


class RuleEngine:
    """
    Evaluates business rules against the simulated after-state.
    Supports HARD (Block), SOFT (Review), and INFO (Log) severities.
    """

    @staticmethod
    def evaluate(
        state: SimulatedState, options: EngineOptions, diagnostics: DiagnosticsData
    ) -> List[RuleResult]:
        results = []

        # 1. CASH_BAND (Soft)
        cash_weight = next(
            (a.weight for a in state.allocation_by_asset_class if a.key == "CASH"), Decimal("0")
        )
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
                    remediation_hint=(
                        "Portfolio has excess cash. Consider investing or verifying exclusions."
                    ),
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
        if options.single_position_max_weight:
            max_w = options.single_position_max_weight
            breach = False
            for pos in state.allocation_by_instrument:
                if pos.weight > max_w + Decimal("0.001"):
                    breach = True
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
            if not breach:
                results.append(
                    RuleResult(
                        rule_id="SINGLE_POSITION_MAX",
                        severity="HARD",
                        status="PASS",
                        measured=Decimal("0"),
                        threshold={"max": max_w},
                        reason_code="OK",
                    )
                )

        # 3. DATA_QUALITY (Hard) - Derived from Diagnostics
        dq_issues = (
            len(diagnostics.data_quality.get("price_missing", []))
            + len(diagnostics.data_quality.get("fx_missing", []))
            + len(diagnostics.data_quality.get("shelf_missing", []))
        )
        if dq_issues > 0:
            results.append(
                RuleResult(
                    rule_id="DATA_QUALITY",
                    severity="HARD",
                    status="FAIL",
                    measured=Decimal(dq_issues),
                    threshold={"max": Decimal("0")},
                    reason_code="MISSING_DATA",
                    remediation_hint="Check diagnostics.data_quality for missing prices/FX.",
                )
            )
        else:
            results.append(
                RuleResult(
                    rule_id="DATA_QUALITY",
                    severity="HARD",
                    status="PASS",
                    measured=Decimal("0"),
                    threshold={"max": Decimal("0")},
                    reason_code="OK",
                )
            )

        # 4. MIN_TRADE_SIZE (Info) - Derived from Diagnostics
        suppressed_count = len(diagnostics.suppressed_intents)
        if suppressed_count > 0:
            results.append(
                RuleResult(
                    rule_id="MIN_TRADE_SIZE",
                    severity="SOFT",  # RFC says INFO or SOFT, usually SOFT if excessive
                    status="PASS",  # Technically a PASS because we suppressed them
                    measured=Decimal(suppressed_count),
                    threshold={"min": Decimal("0")},
                    reason_code="INTENTS_SUPPRESSED",
                    remediation_hint="Trades were suppressed due to dust thresholds.",
                )
            )
        else:
            results.append(
                RuleResult(
                    rule_id="MIN_TRADE_SIZE",
                    severity="SOFT",
                    status="PASS",
                    measured=Decimal("0"),
                    threshold={"min": Decimal("0")},
                    reason_code="OK",
                )
            )

        return results
