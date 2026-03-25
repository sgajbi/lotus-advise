from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from src.core.models import GateDecision, ProposalResult, ProposalSimulateRequest

WorkspaceInputMode = Literal["stateless", "stateful"]
WorkspaceLifecycleState = Literal["ACTIVE", "PAUSED", "ARCHIVED"]


class WorkspaceStatelessInput(BaseModel):
    simulate_request: ProposalSimulateRequest = Field(
        description=(
            "Full advisory simulation payload supplied directly by the caller for sandbox, replay, "
            "or external integration workflows."
        ),
        examples=[
            {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "250000"}],
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        ],
    )


class WorkspaceStatefulInput(BaseModel):
    portfolio_id: str = Field(
        description="Canonical Lotus portfolio identifier resolved through upstream services.",
        examples=["pf_advisory_01"],
    )
    as_of: str = Field(
        description="Business date or timestamp used to resolve the source portfolio context.",
        examples=["2026-03-25"],
    )
    household_id: Optional[str] = Field(
        default=None,
        description="Optional household identifier when the advisory workflow is household-scoped.",
        examples=["hh_001"],
    )
    mandate_id: Optional[str] = Field(
        default=None,
        description="Optional mandate identifier used to enrich the advisory context.",
        examples=["mandate_growth_01"],
    )
    benchmark_id: Optional[str] = Field(
        default=None,
        description="Optional benchmark identifier for context-aware evaluation and comparison.",
        examples=["benchmark_balanced_usd"],
    )


class WorkspaceResolvedContext(BaseModel):
    portfolio_id: str = Field(
        description="Resolved portfolio identifier used by the workspace evaluation.",
        examples=["pf_advisory_01"],
    )
    as_of: str = Field(
        description="Resolved business date or timestamp used during evaluation.",
        examples=["2026-03-25"],
    )
    portfolio_snapshot_id: Optional[str] = Field(
        default=None,
        description="Upstream portfolio snapshot identifier captured for replay and audit.",
        examples=["ps_20260325_001"],
    )
    market_data_snapshot_id: Optional[str] = Field(
        default=None,
        description="Upstream market-data snapshot identifier captured for replay and audit.",
        examples=["md_20260325_001"],
    )
    risk_context_id: Optional[str] = Field(
        default=None,
        description="Optional upstream risk-context identifier used for advisory enrichment.",
        examples=["risk_ctx_001"],
    )
    reporting_context_id: Optional[str] = Field(
        default=None,
        description="Optional reporting-context identifier used to correlate downstream report generation.",
        examples=["report_ctx_001"],
    )


class WorkspaceEvaluationImpactSummary(BaseModel):
    portfolio_value_delta_base_ccy: str = Field(
        description="Formatted base-currency delta between source portfolio value and current draft evaluation.",
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
        description="Count of review issues that currently require human review but do not block evaluation.",
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


class WorkspaceSessionCreateRequest(BaseModel):
    workspace_name: str = Field(
        description="Advisor-facing workspace name used in Lotus advisory workflows.",
        examples=["Q2 2026 growth reallocation draft"],
    )
    created_by: str = Field(
        description="Actor identifier for the advisor or reviewer creating the workspace.",
        examples=["advisor_123"],
    )
    input_mode: WorkspaceInputMode = Field(
        description="Workspace input mode determining whether context is supplied directly or resolved upstream.",
        examples=["stateful"],
    )
    stateless_input: Optional[WorkspaceStatelessInput] = Field(
        default=None,
        description="Direct advisory input payload for stateless workspace sessions.",
        examples=[
            {
                "simulate_request": {
                    "portfolio_snapshot": {
                        "portfolio_id": "pf_advisory_01",
                        "base_currency": "USD",
                    },
                    "market_data_snapshot": {"prices": [], "fx_rates": []},
                    "shelf_entries": [],
                    "options": {"enable_proposal_simulation": True},
                    "proposed_cash_flows": [],
                    "proposed_trades": [],
                }
            }
        ],
    )
    stateful_input: Optional[WorkspaceStatefulInput] = Field(
        default=None,
        description="Identifier-based input payload for stateful workspace sessions.",
        examples=[
            {
                "portfolio_id": "pf_advisory_01",
                "household_id": "hh_001",
                "as_of": "2026-03-25",
                "mandate_id": "mandate_growth_01",
            }
        ],
    )

    @model_validator(mode="after")
    def validate_input_mode_payloads(self) -> "WorkspaceSessionCreateRequest":
        if self.input_mode == "stateless":
            if self.stateless_input is None or self.stateful_input is not None:
                raise ValueError(
                    "stateless workspaces require stateless_input and must not include stateful_input"
                )
        if self.input_mode == "stateful":
            if self.stateful_input is None or self.stateless_input is not None:
                raise ValueError(
                    "stateful workspaces require stateful_input and must not include stateless_input"
                )
        return self


class WorkspaceSession(BaseModel):
    workspace_id: str = Field(
        description="Workspace session identifier.",
        examples=["aws_001"],
    )
    workspace_name: str = Field(
        description="Advisor-facing workspace name.",
        examples=["Q2 2026 growth reallocation draft"],
    )
    lifecycle_state: WorkspaceLifecycleState = Field(
        description="Lifecycle state of the advisory workspace session.",
        examples=["ACTIVE"],
    )
    input_mode: WorkspaceInputMode = Field(
        description="Workspace input mode for this session.",
        examples=["stateful"],
    )
    created_by: str = Field(
        description="Actor identifier for the user that created the workspace.",
        examples=["advisor_123"],
    )
    created_at: str = Field(
        description="UTC ISO8601 timestamp of workspace creation.",
        examples=["2026-03-25T09:30:00+00:00"],
    )
    stateless_input: Optional[WorkspaceStatelessInput] = Field(
        default=None,
        description="Direct input payload for stateless workspaces.",
    )
    stateful_input: Optional[WorkspaceStatefulInput] = Field(
        default=None,
        description="Identifier-based input payload for stateful workspaces.",
    )
    resolved_context: Optional[WorkspaceResolvedContext] = Field(
        default=None,
        description="Resolved advisory context captured for replay and audit.",
    )
    evaluation_summary: Optional[WorkspaceEvaluationSummary] = Field(
        default=None,
        description="Current workspace evaluation summary for advisor and reviewer workflows.",
    )
    latest_proposal_result: Optional[ProposalResult] = Field(
        default=None,
        description="Optional latest full proposal result associated with the workspace draft.",
    )

    @model_validator(mode="after")
    def validate_session_mode_payloads(self) -> "WorkspaceSession":
        if self.input_mode == "stateless":
            if self.stateless_input is None or self.stateful_input is not None:
                raise ValueError(
                    "stateless workspace sessions require stateless_input and must not include stateful_input"
                )
        if self.input_mode == "stateful":
            if self.stateful_input is None or self.stateless_input is not None:
                raise ValueError(
                    "stateful workspace sessions require stateful_input and must not include stateless_input"
                )
        return self


class WorkspaceSessionCreateResponse(BaseModel):
    workspace: WorkspaceSession = Field(
        description="Created advisory workspace session.",
    )
