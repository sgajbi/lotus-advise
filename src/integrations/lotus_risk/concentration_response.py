from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from src.core.models import ProposalResult


class LotusRiskConcentrationRiskProxy(BaseModel):
    hhi_current: Decimal
    hhi_proposed: Decimal
    hhi_delta: Decimal


class LotusRiskPositionDescriptor(BaseModel):
    security_id: str | None = None
    security_name: str | None = None
    weight: Decimal


class LotusRiskIssuerDescriptor(BaseModel):
    issuer_id: str | None = None
    issuer_name: str | None = None
    weight: Decimal


class LotusRiskSinglePositionConcentration(BaseModel):
    top_position_weight_current: Decimal
    top_position_weight_proposed: Decimal
    top_position_weight_delta: Decimal
    top_n_cumulative_weight_current: Decimal
    top_n_cumulative_weight_proposed: Decimal
    top_n_cumulative_weight_delta: Decimal
    top_n: int
    top_position_current: LotusRiskPositionDescriptor | None = None
    top_position_proposed: LotusRiskPositionDescriptor | None = None


class LotusRiskIssuerConcentration(BaseModel):
    hhi_current: Decimal
    hhi_proposed: Decimal
    hhi_delta: Decimal
    top_issuer_weight_current: Decimal
    top_issuer_weight_proposed: Decimal
    top_issuer_weight_delta: Decimal
    coverage_status: str
    coverage_ratio_current: Decimal | None = None
    coverage_ratio_proposed: Decimal | None = None
    covered_position_count_current: int
    covered_position_count_proposed: int
    total_position_count_current: int
    total_position_count_proposed: int
    uncovered_position_count_current: int | None = None
    uncovered_position_count_proposed: int | None = None
    top_issuer_current: LotusRiskIssuerDescriptor | None = None
    top_issuer_proposed: LotusRiskIssuerDescriptor | None = None
    note: str | None = None


class LotusRiskConcentrationResponse(BaseModel):
    source_service: str = Field(pattern="^lotus-risk$")
    input_mode: str = Field(pattern="^(simulation|stateless)$")
    risk_proxy: LotusRiskConcentrationRiskProxy
    single_position_concentration: LotusRiskSinglePositionConcentration
    issuer_concentration: LotusRiskIssuerConcentration
    valuation_context: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


def apply_concentration_response(
    *,
    proposal_result: ProposalResult,
    concentration: LotusRiskConcentrationResponse,
) -> ProposalResult:
    explanation = dict(proposal_result.explanation)
    explanation["risk_lens"] = {
        "source_service": concentration.source_service,
        "input_mode": concentration.input_mode,
        "risk_proxy": concentration.risk_proxy.model_dump(mode="json"),
        "single_position_concentration": (
            concentration.single_position_concentration.model_dump(mode="json")
        ),
        "issuer_concentration": concentration.issuer_concentration.model_dump(mode="json"),
        "valuation_context": concentration.valuation_context,
        "metadata": concentration.metadata,
    }
    proposal_result.explanation = explanation
    return proposal_result
