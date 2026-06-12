from decimal import Decimal

import pytest

from src.core.common.suitability import compute_suitability_result
from src.core.models import AllocationMetric, EngineOptions, Money, ShelfEntry, SimulatedState


def _metric(key: str, weight: str) -> AllocationMetric:
    return AllocationMetric(
        key=key,
        weight=Decimal(weight),
        value=Money(amount=Decimal("100"), currency="USD"),
    )


def _state(*, instrument_weights: dict[str, str], cash_weight: str = "0.05") -> SimulatedState:
    non_cash_weight = Decimal("1") - Decimal(cash_weight)
    return SimulatedState(
        total_value=Money(amount=Decimal("1000"), currency="USD"),
        cash_balances=[],
        positions=[],
        allocation_by_asset_class=[
            _metric("EQUITY", str(non_cash_weight)),
            _metric("CASH", cash_weight),
        ],
        allocation_by_instrument=[
            _metric(instrument_id, weight)
            for instrument_id, weight in sorted(instrument_weights.items())
        ],
        allocation=[
            _metric(instrument_id, weight)
            for instrument_id, weight in sorted(instrument_weights.items())
        ],
        allocation_by_attribute={},
    )


@pytest.mark.parametrize(
    ("allow_restricted", "expected_severity", "expected_gate", "expected_allow_value"),
    [
        (False, "HIGH", "COMPLIANCE_REVIEW", "false"),
        (True, "MEDIUM", "RISK_REVIEW", "true"),
    ],
)
def test_suitability_restricted_increase_respects_allowed_posture(
    allow_restricted: bool,
    expected_severity: str,
    expected_gate: str,
    expected_allow_value: str,
) -> None:
    before = _state(instrument_weights={"EQ_RESTRICTED": "0.05", "EQ_B": "0.95"})
    after = _state(instrument_weights={"EQ_RESTRICTED": "0.10", "EQ_B": "0.90"})
    options = EngineOptions(
        allow_restricted=allow_restricted,
        suitability_thresholds={
            "single_position_max_weight": "1.00",
            "issuer_max_weight": "1.00",
            "max_weight_by_liquidity_tier": {},
            "cash_band_min_weight": "0",
            "cash_band_max_weight": "1",
        },
    )

    result = compute_suitability_result(
        before=before,
        after=after,
        shelf=[
            ShelfEntry(
                instrument_id="EQ_RESTRICTED",
                status="RESTRICTED",
                issuer_id="ISS_RESTRICTED",
                liquidity_tier="L1",
            ),
            ShelfEntry(
                instrument_id="EQ_B",
                status="APPROVED",
                issuer_id="ISS_B",
                liquidity_tier="L1",
            ),
        ],
        options=options,
        portfolio_snapshot_id=f"pf_restricted_{expected_allow_value}",
        market_data_snapshot_id=f"md_restricted_{expected_allow_value}",
    )

    issue = result.issues[0]
    assert issue.issue_id == "SUIT_GOVERNANCE_RESTRICTED_INCREASE"
    assert issue.severity == expected_severity
    assert issue.approval_implication == expected_gate
    assert issue.details["allow_restricted"] == expected_allow_value
    assert result.recommended_gate == expected_gate
