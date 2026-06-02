from decimal import Decimal
from typing import Any, cast

from src.core.advisory.artifact_formatting import quantized_weight_str
from src.core.advisory.artifact_models import (
    ProposalArtifactPortfolioState,
    ProposalArtifactWeightChange,
)

ZERO_WEIGHT = Decimal("0")


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
    before_by_id = {row.key: row.weight for row in before_state.allocation_by_instrument}
    after_by_id = {row.key: row.weight for row in after_state.allocation_by_instrument}
    rows = []
    for instrument_id in sorted(set(before_by_id) | set(after_by_id)):
        before_weight = before_by_id.get(instrument_id, ZERO_WEIGHT)
        after_weight = after_by_id.get(instrument_id, ZERO_WEIGHT)
        delta = after_weight - before_weight
        if delta == ZERO_WEIGHT:
            continue
        rows.append((instrument_id, before_weight, after_weight, delta))
    rows.sort(key=lambda item: (-abs(item[3]), item[0]))
    return [
        ProposalArtifactWeightChange(
            bucket_type="INSTRUMENT",
            bucket_id=instrument_id,
            weight_before=quantized_weight_str(before_weight),
            weight_after=quantized_weight_str(after_weight),
            delta=quantized_weight_str(delta),
        )
        for instrument_id, before_weight, after_weight, delta in rows[:limit]
    ]


def cash_weight(state: Any) -> Decimal:
    for row in state.allocation_by_asset_class:
        if row.key == "CASH":
            return cast(Decimal, row.weight)
    return ZERO_WEIGHT
