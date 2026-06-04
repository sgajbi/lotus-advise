from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.core.proposals.memo_foundational_summaries import (
    alternatives_summary,
    decision_summary_text,
    objective_summary,
    recommendation_summary,
    risk_summary,
)
from src.core.proposals.memo_models import (
    ProposalMemoAudience,
    ProposalMemoMaterialClaim,
    ProposalMemoSection,
    ProposalMemoSourceAuthorityManifest,
)

SectionFactory = Callable[..., ProposalMemoSection]
ClaimsFactory = Callable[..., list[ProposalMemoMaterialClaim]]

_ALL_INTERNAL_AUDIENCES: list[ProposalMemoAudience] = [
    "ADVISOR",
    "COMPLIANCE",
    "INVESTMENT_DESK",
    "OPERATIONS",
    "AUDIT",
    "SALES_PRE_SALES",
]
_REVIEW_AUDIENCES: list[ProposalMemoAudience] = [
    "ADVISOR",
    "COMPLIANCE",
    "INVESTMENT_DESK",
    "AUDIT",
]


def build_foundational_memo_sections(
    *,
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
    section_factory: SectionFactory,
    claims_factory: ClaimsFactory,
) -> list[ProposalMemoSection]:
    return [
        _build_executive_summary_section(
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            section_factory=section_factory,
            claims_factory=claims_factory,
        ),
        _build_client_context_section(
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            section_factory=section_factory,
        ),
        _build_advisory_objective_section(
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            section_factory=section_factory,
            claims_factory=claims_factory,
        ),
        _build_recommendation_section(
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            section_factory=section_factory,
            claims_factory=claims_factory,
        ),
        _build_rejected_alternatives_section(
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            section_factory=section_factory,
            claims_factory=claims_factory,
        ),
        _build_portfolio_impact_section(
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            section_factory=section_factory,
            claims_factory=claims_factory,
        ),
        _build_risk_context_section(
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            section_factory=section_factory,
            claims_factory=claims_factory,
        ),
    ]


def _build_executive_summary_section(
    *,
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
    section_factory: SectionFactory,
    claims_factory: ClaimsFactory,
) -> ProposalMemoSection:
    summary = decision_summary_text(artifact)
    return section_factory(
        section_id="EXECUTIVE_SUMMARY",
        title="Executive Summary",
        owner_role="advisor",
        audience_visibility=_ALL_INTERNAL_AUDIENCES,
        source_keys=["advise_decision_summary"],
        artifact=artifact,
        evidence_bundle=evidence_bundle,
        source_manifest=source_manifest,
        summary=summary,
        claims=claims_factory(
            section_id="EXECUTIVE_SUMMARY",
            evidence_refs=["artifact.proposal_decision_summary"],
            source_refs=["lotus-advise:proposal_decision_summary"],
            texts=[summary],
            reason_codes=["ADVISE_DECISION_SUMMARY_CAPTURED"],
        ),
    )


def _build_client_context_section(
    *,
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
    section_factory: SectionFactory,
) -> ProposalMemoSection:
    return section_factory(
        section_id="CLIENT_AND_HOUSEHOLD_CONTEXT",
        title="Client And Household Context",
        owner_role="relationship_manager",
        audience_visibility=_REVIEW_AUDIENCES,
        source_keys=["core_household_account_mandate_objective_restrictions"],
        artifact=artifact,
        evidence_bundle=evidence_bundle,
        source_manifest=source_manifest,
        summary="Client, household, account, mandate, objectives, and restrictions source posture.",
        claims=[],
    )


def _build_advisory_objective_section(
    *,
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
    section_factory: SectionFactory,
    claims_factory: ClaimsFactory,
) -> ProposalMemoSection:
    summary = objective_summary(artifact)
    return section_factory(
        section_id="ADVISORY_OBJECTIVE_AND_CONSTRAINTS",
        title="Advisory Objective And Constraints",
        owner_role="advisor",
        audience_visibility=_REVIEW_AUDIENCES,
        source_keys=["core_household_account_mandate_objective_restrictions"],
        artifact=artifact,
        evidence_bundle=evidence_bundle,
        source_manifest=source_manifest,
        summary=summary,
        claims=claims_factory(
            section_id="ADVISORY_OBJECTIVE_AND_CONSTRAINTS",
            evidence_refs=["artifact.summary.objective_tags"],
            source_refs=["lotus-advise:proposal_artifact"],
            texts=[summary],
            reason_codes=["ADVISE_OBJECTIVE_TAGS_CAPTURED"],
        ),
    )


def _build_recommendation_section(
    *,
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
    section_factory: SectionFactory,
    claims_factory: ClaimsFactory,
) -> ProposalMemoSection:
    summary = recommendation_summary(artifact)
    return section_factory(
        section_id="RECOMMENDATION",
        title="Recommendation",
        owner_role="advisor",
        audience_visibility=_REVIEW_AUDIENCES,
        source_keys=[
            "advise_decision_summary",
            "advise_alternatives_lifecycle_execution_boundary",
        ],
        artifact=artifact,
        evidence_bundle=evidence_bundle,
        source_manifest=source_manifest,
        summary=summary,
        claims=claims_factory(
            section_id="RECOMMENDATION",
            evidence_refs=[
                "artifact.proposal_decision_summary",
                "artifact.summary.recommended_next_step",
            ],
            source_refs=["lotus-advise:proposal_decision_summary"],
            texts=[summary],
            reason_codes=["ADVISE_RECOMMENDATION_CAPTURED"],
        ),
    )


def _build_rejected_alternatives_section(
    *,
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
    section_factory: SectionFactory,
    claims_factory: ClaimsFactory,
) -> ProposalMemoSection:
    summary = alternatives_summary(artifact)
    return section_factory(
        section_id="REJECTED_ALTERNATIVES",
        title="Rejected Alternatives",
        owner_role="investment_desk",
        audience_visibility=_REVIEW_AUDIENCES,
        source_keys=["advise_alternatives_lifecycle_execution_boundary"],
        artifact=artifact,
        evidence_bundle=evidence_bundle,
        source_manifest=source_manifest,
        summary=summary,
        claims=claims_factory(
            section_id="REJECTED_ALTERNATIVES",
            evidence_refs=["artifact.proposal_alternatives.alternatives"],
            source_refs=["lotus-advise:proposal_alternatives"],
            texts=[summary],
            reason_codes=["ADVISE_ALTERNATIVES_CAPTURED"],
        ),
    )


def _build_portfolio_impact_section(
    *,
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
    section_factory: SectionFactory,
    claims_factory: ClaimsFactory,
) -> ProposalMemoSection:
    return section_factory(
        section_id="PORTFOLIO_IMPACT",
        title="Portfolio Impact",
        owner_role="advisor",
        audience_visibility=_REVIEW_AUDIENCES,
        source_keys=["core_portfolio_holdings_cash", "core_market_prices", "core_fx_rates"],
        artifact=artifact,
        evidence_bundle=evidence_bundle,
        source_manifest=source_manifest,
        summary="Before and after portfolio impact is projected from proposal artifact evidence.",
        claims=claims_factory(
            section_id="PORTFOLIO_IMPACT",
            evidence_refs=["artifact.portfolio_impact"],
            source_refs=["lotus-core:portfolio_state", "lotus-advise:proposal_artifact"],
            texts=["Portfolio impact uses the immutable proposal artifact before/after evidence."],
            reason_codes=["PORTFOLIO_IMPACT_CAPTURED"],
        ),
    )


def _build_risk_context_section(
    *,
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
    section_factory: SectionFactory,
    claims_factory: ClaimsFactory,
) -> ProposalMemoSection:
    summary = risk_summary(artifact)
    return section_factory(
        section_id="RISK_AND_SCENARIO_CONTEXT",
        title="Risk And Scenario Context",
        owner_role="risk_reviewer",
        audience_visibility=_REVIEW_AUDIENCES,
        source_keys=[
            "risk_concentration",
            "risk_drawdown_stress_liquidity_private_assets_climate_geopolitical",
        ],
        artifact=artifact,
        evidence_bundle=evidence_bundle,
        source_manifest=source_manifest,
        summary=summary,
        claims=claims_factory(
            section_id="RISK_AND_SCENARIO_CONTEXT",
            evidence_refs=["artifact.risk_lens", "evidence_bundle.risk_lens"],
            source_refs=["lotus-risk:risk_lens"],
            texts=[summary],
            reason_codes=["RISK_LENS_CAPTURED"],
        ),
    )
