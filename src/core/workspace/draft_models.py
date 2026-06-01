from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.core.advisory.alternatives_models import ProposalAlternativesRequest
from src.core.engine_options_models import EngineOptions
from src.core.gate_models import GateDecision
from src.core.portfolio_models import ReferenceModel
from src.core.proposal_request_models import ProposedCashFlow, ProposedTrade


class WorkspaceTradeDraft(BaseModel):
    workspace_trade_id: str = Field(
        description="Workspace-local trade identifier used for deterministic draft editing.",
        examples=["wtd_001"],
    )
    trade: ProposedTrade = Field(
        description="Advisor-entered trade currently included in the workspace draft.",
    )


class WorkspaceCashFlowDraft(BaseModel):
    workspace_cash_flow_id: str = Field(
        description="Workspace-local cash-flow identifier used for deterministic draft editing.",
        examples=["wcf_001"],
    )
    cash_flow: ProposedCashFlow = Field(
        description="Advisor-entered cash-flow currently included in the workspace draft.",
    )


class WorkspaceDraftState(BaseModel):
    options: EngineOptions = Field(
        default_factory=EngineOptions,
        description="Current workspace-level evaluation options.",
    )
    alternatives_request: ProposalAlternativesRequest | None = Field(
        default=None,
        description="Optional proposal alternatives request currently attached to the workspace.",
    )
    reference_model: Optional[ReferenceModel] = Field(
        default=None,
        description="Optional reference model currently attached to the workspace draft.",
    )
    trade_drafts: list[WorkspaceTradeDraft] = Field(
        default_factory=list,
        description="Current ordered trade draft items in the workspace.",
    )
    cash_flow_drafts: list[WorkspaceCashFlowDraft] = Field(
        default_factory=list,
        description="Current ordered cash-flow draft items in the workspace.",
    )


class WorkspaceEvaluationImpactSummary(BaseModel):
    portfolio_value_delta_base_ccy: str = Field(
        description=(
            "Formatted base-currency delta between source portfolio value and current draft "
            "evaluation."
        ),
        examples=["-1250.50"],
    )
    trade_count: int = Field(
        description="Number of current draft trades in the workspace.",
        examples=[3],
    )
    cash_flow_count: int = Field(
        description="Number of current draft cash-flow actions in the workspace.",
        examples=[1],
    )


class WorkspaceEvaluationSummary(BaseModel):
    status: Literal["READY", "PENDING_REVIEW", "BLOCKED"] = Field(
        description="Top-level advisory workflow posture for the current workspace draft.",
        examples=["PENDING_REVIEW"],
    )
    gate_decision: Optional[GateDecision] = Field(
        default=None,
        description="Optional gate decision derived from the current draft evaluation.",
    )
    blocking_issue_count: int = Field(
        default=0,
        ge=0,
        description="Count of blocking issues that currently prevent workflow progression.",
        examples=[1],
    )
    review_issue_count: int = Field(
        default=0,
        ge=0,
        description=(
            "Count of review issues that currently require human review but do not block "
            "evaluation."
        ),
        examples=[2],
    )
    impact_summary: WorkspaceEvaluationImpactSummary = Field(
        description="Compact portfolio-impact summary for workspace cards and list views.",
        examples=[
            {
                "portfolio_value_delta_base_ccy": "-1250.50",
                "trade_count": 3,
                "cash_flow_count": 1,
            }
        ],
    )
