from dataclasses import dataclass
from decimal import Decimal
from typing import Any, cast

from src.core.advisory.artifact_formatting import quantized_weight_str
from src.core.advisory.artifact_portfolio_models import (
    ProposalArtifactPortfolioState,
    ProposalArtifactWeightChange,
)

ZERO_WEIGHT = Decimal("0")


@dataclass(frozen=True)
class WeightChangeRow:
    instrument_id: str
    before_weight: Decimal
    after_weight: Decimal
    delta: Decimal


def sorted_allocations(allocations: list[Any]) -> list[Any]:
    return sorted(allocations, key=lambda item: (-item.weight, item.key))


def build_portfolio_state_payload(state: Any) -> ProposalArtifactPortfolioState:
    return ProposalArtifactPortfolioState(
        total_value=state.total_value,
        allocation_by_asset_class=[
            item.model_dump(mode="json")
            for item in sorted_allocations(state.allocation_by_asset_class)
        ],
        allocation_by_instrument=[
            item.model_dump(mode="json")
            for item in sorted_allocations(state.allocation_by_instrument)
        ],
    )


def largest_weight_changes(
    before_state: Any, after_state: Any, *, limit: int
) -> list[ProposalArtifactWeightChange]:
    rows = _sorted_weight_change_rows(before_state, after_state)
    return [_weight_change_payload(row) for row in rows[:limit]]


def _allocation_weights_by_id(state: Any) -> dict[str, Decimal]:
    return {row.key: row.weight for row in state.allocation_by_instrument}


def _sorted_weight_change_rows(before_state: Any, after_state: Any) -> list[WeightChangeRow]:
    before_by_id = _allocation_weights_by_id(before_state)
    after_by_id = _allocation_weights_by_id(after_state)
    rows = [
        row
        for instrument_id in sorted(set(before_by_id) | set(after_by_id))
        if (row := _weight_change_row(instrument_id, before_by_id, after_by_id)) is not None
    ]
    return sorted(rows, key=lambda row: (-abs(row.delta), row.instrument_id))


def _weight_change_row(
    instrument_id: str,
    before_by_id: dict[str, Decimal],
    after_by_id: dict[str, Decimal],
) -> WeightChangeRow | None:
    before_weight = before_by_id.get(instrument_id, ZERO_WEIGHT)
    after_weight = after_by_id.get(instrument_id, ZERO_WEIGHT)
    delta = after_weight - before_weight
    if delta == ZERO_WEIGHT:
        return None
    return WeightChangeRow(
        instrument_id=instrument_id,
        before_weight=before_weight,
        after_weight=after_weight,
        delta=delta,
    )


def _weight_change_payload(row: WeightChangeRow) -> ProposalArtifactWeightChange:
    return ProposalArtifactWeightChange(
        bucket_type="INSTRUMENT",
        bucket_id=row.instrument_id,
        weight_before=quantized_weight_str(row.before_weight),
        weight_after=quantized_weight_str(row.after_weight),
        delta=quantized_weight_str(row.delta),
    )


def cash_weight(state: Any) -> Decimal:
    for row in state.allocation_by_asset_class:
        if row.key == "CASH":
            return cast(Decimal, row.weight)
    return ZERO_WEIGHT
