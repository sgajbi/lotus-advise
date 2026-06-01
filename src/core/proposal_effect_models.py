from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.core.portfolio_models import Money


class Reconciliation(BaseModel):
    before_total_value: Money = Field(description="Before-state total value.")
    after_total_value: Money = Field(description="After-state total value.")
    delta: Money = Field(description="After minus before.")
    tolerance: Money = Field(description="Allowed reconciliation tolerance.")
    status: Literal["OK", "MISMATCH"] = Field(description="Reconciliation outcome.")


class TaxImpact(BaseModel):
    total_realized_gain: Money = Field(
        description="Aggregate realized gain from constrained sell allocation."
    )
    total_realized_loss: Money = Field(
        description="Aggregate realized loss from constrained sell allocation."
    )
    budget_limit: Optional[Money] = Field(default=None, description="Configured gains budget.")
    budget_used: Optional[Money] = Field(default=None, description="Portion of budget consumed.")


__all__ = [
    "Reconciliation",
    "TaxImpact",
]
