from __future__ import annotations

from typing import Any, Literal, Mapping, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.core.advisory.policy_context import (
    CLIENT_CONTEXT_STATUS,
    JURISDICTION_CONTEXT_STATUS,
    MANDATE_CONTEXT_STATUS,
)

SimulationAuthority = Literal["lotus_core", "lotus_advise_local_fallback"]
RiskAuthority = Literal["lotus_risk", "unavailable"]
PolicyContextStatus = Literal["AVAILABLE", "MISSING"]

AUTHORITY_RESOLUTION_EXPLANATION_KEY = "authority_resolution"
ADVISORY_POLICY_CONTEXT_EXPLANATION_KEY = "advisory_policy_context"


class AuthorityResolutionExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    simulation_authority: SimulationAuthority = Field(
        description="Service authority used for canonical proposal simulation.",
    )
    risk_authority: RiskAuthority = Field(
        description="Service authority used for canonical risk enrichment.",
    )
    degraded: bool = Field(
        description="Whether any required upstream authority was degraded for this proposal run.",
    )
    degraded_reasons: list[str] = Field(
        default_factory=list,
        description="Stable degraded reason codes emitted by unavailable upstream authorities.",
    )

    @model_validator(mode="after")
    def _degraded_flag_matches_reasons(self) -> AuthorityResolutionExplanation:
        if self.degraded != bool(self.degraded_reasons):
            raise ValueError("degraded must match whether degraded_reasons is non-empty")
        if self.risk_authority == "unavailable" and not self.degraded:
            raise ValueError("unavailable risk_authority requires degraded=true")
        return self


class AdvisoryPolicyContextExplanation(BaseModel):
    model_config = ConfigDict(extra="allow")

    input_mode: str | None = Field(
        default=None,
        description="Input mode used when resolving advisory policy context.",
    )
    context_source: str | None = Field(
        default=None,
        description="Source authority used for advisory policy context resolution.",
    )
    client_context_status: PolicyContextStatus | None = Field(
        default=None,
        alias=CLIENT_CONTEXT_STATUS,
        description="Whether client context was available for policy evaluation.",
    )
    mandate_context_status: PolicyContextStatus | None = Field(
        default=None,
        alias=MANDATE_CONTEXT_STATUS,
        description="Whether mandate context was available for policy evaluation.",
    )
    jurisdiction_context_status: PolicyContextStatus | None = Field(
        default=None,
        alias=JURISDICTION_CONTEXT_STATUS,
        description="Whether jurisdiction context was available for policy evaluation.",
    )
    household_id: str | None = Field(
        default=None,
        description="Resolved household identifier, when available.",
    )
    mandate_id: str | None = Field(
        default=None,
        description="Resolved mandate identifier, when available.",
    )
    jurisdiction: str | None = Field(
        default=None,
        description="Resolved advisory jurisdiction, when available.",
    )
    legal_entity_code: str | None = Field(
        default=None,
        description="Resolved booking or legal entity code, when available.",
    )
    benchmark_id: str | None = Field(
        default=None,
        description="Resolved benchmark identifier, when available.",
    )
    missing_context: list[str] = Field(
        default_factory=list,
        description="Stable missing-context reason codes for unavailable policy context.",
    )


def build_authority_resolution_explanation(
    *,
    simulation_authority: str,
    risk_authority: str,
    degraded_reasons: list[str],
) -> AuthorityResolutionExplanation:
    return cast(
        AuthorityResolutionExplanation,
        AuthorityResolutionExplanation.model_validate(
            {
                "simulation_authority": simulation_authority,
                "risk_authority": risk_authority,
                "degraded": bool(degraded_reasons),
                "degraded_reasons": degraded_reasons,
            }
        ),
    )


def attach_governed_explanation_sections(
    *,
    explanation: Mapping[str, Any],
    authority_resolution: AuthorityResolutionExplanation,
    policy_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    updated = dict(explanation)
    updated[AUTHORITY_RESOLUTION_EXPLANATION_KEY] = authority_resolution.model_dump()
    if policy_context is not None:
        policy_context_section = AdvisoryPolicyContextExplanation.model_validate(policy_context)
        updated[ADVISORY_POLICY_CONTEXT_EXPLANATION_KEY] = policy_context_section.model_dump(
            by_alias=True,
            exclude_none=True,
        )
    return updated


def authority_resolution_from_explanation(
    explanation: Mapping[str, Any],
) -> AuthorityResolutionExplanation | None:
    section = explanation.get(AUTHORITY_RESOLUTION_EXPLANATION_KEY)
    if section is None:
        return None
    return cast(
        AuthorityResolutionExplanation,
        AuthorityResolutionExplanation.model_validate(section),
    )


def policy_context_from_explanation(
    explanation: Mapping[str, Any],
) -> AdvisoryPolicyContextExplanation | None:
    section = explanation.get(ADVISORY_POLICY_CONTEXT_EXPLANATION_KEY)
    if section is None:
        return None
    return cast(
        AdvisoryPolicyContextExplanation,
        AdvisoryPolicyContextExplanation.model_validate(section),
    )


__all__ = [
    "ADVISORY_POLICY_CONTEXT_EXPLANATION_KEY",
    "AUTHORITY_RESOLUTION_EXPLANATION_KEY",
    "AdvisoryPolicyContextExplanation",
    "AuthorityResolutionExplanation",
    "RiskAuthority",
    "SimulationAuthority",
    "attach_governed_explanation_sections",
    "authority_resolution_from_explanation",
    "build_authority_resolution_explanation",
    "policy_context_from_explanation",
]
