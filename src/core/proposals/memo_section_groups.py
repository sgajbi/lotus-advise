from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.core.proposals.memo_models import (
    ProposalMemoAudience,
    ProposalMemoMaterialClaim,
    ProposalMemoSection,
    ProposalMemoSectionKey,
    ProposalMemoSourceAuthorityManifest,
)
from src.core.proposals.memo_policy_enrichment import (
    build_conflict_disclosure_enrichment,
    build_fee_cost_tax_friction_enrichment,
    build_suitability_best_interest_enrichment,
)

SectionFactory = Callable[..., ProposalMemoSection]
AppendixFactory = Callable[
    [
        ProposalMemoSectionKey,
        str,
        str,
        list[ProposalMemoAudience],
        dict[str, Any],
        dict[str, Any],
        ProposalMemoSourceAuthorityManifest,
    ],
    ProposalMemoSection,
]
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
_OPERATIONS_AUDIENCES: list[ProposalMemoAudience] = [
    "ADVISOR",
    "OPERATIONS",
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
    decision_summary = _decision_summary_text(artifact)
    objective_summary = _objective_summary(artifact)
    recommendation_summary = _recommendation_summary(artifact)
    alternatives_summary = _alternatives_summary(artifact)
    risk_summary = _risk_summary(artifact)
    return [
        section_factory(
            section_id="EXECUTIVE_SUMMARY",
            title="Executive Summary",
            owner_role="advisor",
            audience_visibility=_ALL_INTERNAL_AUDIENCES,
            source_keys=["advise_decision_summary"],
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            summary=decision_summary,
            claims=claims_factory(
                section_id="EXECUTIVE_SUMMARY",
                evidence_refs=["artifact.proposal_decision_summary"],
                source_refs=["lotus-advise:proposal_decision_summary"],
                texts=[decision_summary],
                reason_codes=["ADVISE_DECISION_SUMMARY_CAPTURED"],
            ),
        ),
        section_factory(
            section_id="CLIENT_AND_HOUSEHOLD_CONTEXT",
            title="Client And Household Context",
            owner_role="relationship_manager",
            audience_visibility=_REVIEW_AUDIENCES,
            source_keys=["core_household_account_mandate_objective_restrictions"],
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            summary=(
                "Client, household, account, mandate, objectives, and restrictions source posture."
            ),
            claims=[],
        ),
        section_factory(
            section_id="ADVISORY_OBJECTIVE_AND_CONSTRAINTS",
            title="Advisory Objective And Constraints",
            owner_role="advisor",
            audience_visibility=_REVIEW_AUDIENCES,
            source_keys=["core_household_account_mandate_objective_restrictions"],
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            summary=objective_summary,
            claims=claims_factory(
                section_id="ADVISORY_OBJECTIVE_AND_CONSTRAINTS",
                evidence_refs=["artifact.summary.objective_tags"],
                source_refs=["lotus-advise:proposal_artifact"],
                texts=[objective_summary],
                reason_codes=["ADVISE_OBJECTIVE_TAGS_CAPTURED"],
            ),
        ),
        section_factory(
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
            summary=recommendation_summary,
            claims=claims_factory(
                section_id="RECOMMENDATION",
                evidence_refs=[
                    "artifact.proposal_decision_summary",
                    "artifact.summary.recommended_next_step",
                ],
                source_refs=["lotus-advise:proposal_decision_summary"],
                texts=[recommendation_summary],
                reason_codes=["ADVISE_RECOMMENDATION_CAPTURED"],
            ),
        ),
        section_factory(
            section_id="REJECTED_ALTERNATIVES",
            title="Rejected Alternatives",
            owner_role="investment_desk",
            audience_visibility=_REVIEW_AUDIENCES,
            source_keys=["advise_alternatives_lifecycle_execution_boundary"],
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            summary=alternatives_summary,
            claims=claims_factory(
                section_id="REJECTED_ALTERNATIVES",
                evidence_refs=["artifact.proposal_alternatives.alternatives"],
                source_refs=["lotus-advise:proposal_alternatives"],
                texts=[alternatives_summary],
                reason_codes=["ADVISE_ALTERNATIVES_CAPTURED"],
            ),
        ),
        section_factory(
            section_id="PORTFOLIO_IMPACT",
            title="Portfolio Impact",
            owner_role="advisor",
            audience_visibility=_REVIEW_AUDIENCES,
            source_keys=["core_portfolio_holdings_cash", "core_market_prices", "core_fx_rates"],
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            summary=(
                "Before and after portfolio impact is projected from proposal artifact evidence."
            ),
            claims=claims_factory(
                section_id="PORTFOLIO_IMPACT",
                evidence_refs=["artifact.portfolio_impact"],
                source_refs=["lotus-core:portfolio_state", "lotus-advise:proposal_artifact"],
                texts=[
                    "Portfolio impact uses the immutable proposal artifact before/after evidence."
                ],
                reason_codes=["PORTFOLIO_IMPACT_CAPTURED"],
            ),
        ),
        section_factory(
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
            summary=risk_summary,
            claims=claims_factory(
                section_id="RISK_AND_SCENARIO_CONTEXT",
                evidence_refs=["artifact.risk_lens", "evidence_bundle.risk_lens"],
                source_refs=["lotus-risk:risk_lens"],
                texts=[risk_summary],
                reason_codes=["RISK_LENS_CAPTURED"],
            ),
        ),
    ]


def build_policy_review_memo_sections(
    *,
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
    section_factory: SectionFactory,
) -> list[ProposalMemoSection]:
    suitability_best_interest = build_suitability_best_interest_enrichment(
        artifact=artifact,
        evidence_bundle=evidence_bundle,
    )
    fee_cost_tax_friction = build_fee_cost_tax_friction_enrichment(artifact=artifact)
    conflict_disclosure = build_conflict_disclosure_enrichment(
        artifact=artifact,
        evidence_bundle=evidence_bundle,
    )
    return [
        section_factory(
            section_id="SUITABILITY_AND_BEST_INTEREST",
            title="Suitability And Best Interest",
            owner_role="compliance_reviewer",
            audience_visibility=_REVIEW_AUDIENCES,
            source_keys=["advise_decision_summary", "core_product_eligibility_complexity"],
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            summary=suitability_best_interest.summary,
            claims=suitability_best_interest.claims,
            forced_status=suitability_best_interest.forced_status,
            forced_missing=suitability_best_interest.forced_missing,
            forced_reasons=suitability_best_interest.forced_reasons,
        ),
        section_factory(
            section_id="FEES_COSTS_TAX_AND_FRICTIONS",
            title="Fees Costs Tax And Frictions",
            owner_role="compliance_reviewer",
            audience_visibility=_REVIEW_AUDIENCES,
            source_keys=["core_product_eligibility_complexity"],
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            summary=fee_cost_tax_friction.summary,
            claims=fee_cost_tax_friction.claims,
            forced_status=fee_cost_tax_friction.forced_status,
            forced_missing=fee_cost_tax_friction.forced_missing,
            forced_reasons=fee_cost_tax_friction.forced_reasons,
        ),
        section_factory(
            section_id="CONFLICTS_AND_DISCLOSURES",
            title="Conflicts And Disclosures",
            owner_role="compliance_reviewer",
            audience_visibility=_REVIEW_AUDIENCES,
            source_keys=["core_product_eligibility_complexity"],
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            summary=conflict_disclosure.summary,
            claims=conflict_disclosure.claims,
            forced_status=conflict_disclosure.forced_status,
            forced_missing=conflict_disclosure.forced_missing,
            forced_reasons=conflict_disclosure.forced_reasons,
        ),
    ]


def build_operational_memo_sections(
    *,
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
    section_factory: SectionFactory,
    claims_factory: ClaimsFactory,
) -> list[ProposalMemoSection]:
    approval_summary = _approval_summary(artifact)
    return [
        section_factory(
            section_id="APPROVALS_CONSENTS_AND_MAKER_CHECKER",
            title="Approvals Consents And Maker Checker",
            owner_role="compliance_reviewer",
            audience_visibility=_REVIEW_AUDIENCES,
            source_keys=[
                "advise_decision_summary",
                "advise_alternatives_lifecycle_execution_boundary",
            ],
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            summary=approval_summary,
            claims=claims_factory(
                section_id="APPROVALS_CONSENTS_AND_MAKER_CHECKER",
                evidence_refs=["artifact.gate_decision", "artifact.proposal_decision_summary"],
                source_refs=["lotus-advise:proposal_lifecycle"],
                texts=[approval_summary],
                reason_codes=["APPROVAL_POSTURE_CAPTURED"],
            ),
        ),
        section_factory(
            section_id="REPORT_ARCHIVE_AND_DELIVERY_READINESS",
            title="Report Archive And Delivery Readiness",
            owner_role="operations",
            audience_visibility=_OPERATIONS_AUDIENCES,
            source_keys=["advise_alternatives_lifecycle_execution_boundary"],
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            summary=(
                "Memo report, render, archive, and delivery readiness requires an approved "
                "advisor-use memo report package; no package request has been recorded for "
                "this memo evidence."
            ),
            claims=[],
            forced_status="BLOCKED",
            forced_missing=["memo_report_package", "memo_render", "memo_archive_record"],
            forced_reasons=["MEMO_REPORT_PACKAGE_NOT_REQUESTED"],
        ),
        section_factory(
            section_id="EXECUTION_HANDOFF_BOUNDARY",
            title="Execution Handoff Boundary",
            owner_role="operations",
            audience_visibility=_OPERATIONS_AUDIENCES,
            source_keys=["advise_alternatives_lifecycle_execution_boundary"],
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            summary=(
                "Execution handoff evidence is advisory posture only, "
                "not downstream execution truth."
            ),
            claims=claims_factory(
                section_id="EXECUTION_HANDOFF_BOUNDARY",
                evidence_refs=[
                    "artifact.trades_and_funding",
                    "evidence_bundle.inputs.proposed_trades",
                ],
                source_refs=["lotus-advise:execution_boundary"],
                texts=[
                    "Execution evidence distinguishes advisory readiness from downstream "
                    "execution ownership."
                ],
                reason_codes=["EXECUTION_BOUNDARY_CAPTURED"],
            ),
        ),
    ]


def build_appendix_memo_sections(
    *,
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
    appendix_factory: AppendixFactory,
) -> list[ProposalMemoSection]:
    return [
        appendix_factory(
            "EVIDENCE_AND_LINEAGE_APPENDIX",
            "Evidence And Lineage Appendix",
            "audit",
            ["AUDIT", "COMPLIANCE", "OPERATIONS"],
            artifact,
            evidence_bundle,
            source_manifest,
        ),
        appendix_factory(
            "COMPLIANCE_APPENDIX",
            "Compliance Appendix",
            "compliance_reviewer",
            ["COMPLIANCE", "AUDIT"],
            artifact,
            evidence_bundle,
            source_manifest,
        ),
        appendix_factory(
            "OPERATIONS_APPENDIX",
            "Operations Appendix",
            "operations",
            ["OPERATIONS", "AUDIT"],
            artifact,
            evidence_bundle,
            source_manifest,
        ),
        appendix_factory(
            "SUPPORTABILITY_APPENDIX",
            "Supportability Appendix",
            "support",
            ["OPERATIONS", "AUDIT"],
            artifact,
            evidence_bundle,
            source_manifest,
        ),
    ]


def _decision_summary_text(artifact: dict[str, Any]) -> str:
    decision = _dict_at(artifact, "proposal_decision_summary")
    return str(
        decision.get("primary_summary")
        or decision.get("summary")
        or "Proposal decision summary is not available from persisted evidence."
    )


def _objective_summary(artifact: dict[str, Any]) -> str:
    tags = _strings(_dict_at(artifact, "summary").get("objective_tags"))
    if not tags:
        return "Advisory objective tags are not available from the proposal artifact."
    return "Proposal objective tags: " + ", ".join(tags) + "."


def _recommendation_summary(artifact: dict[str, Any]) -> str:
    decision = _dict_at(artifact, "proposal_decision_summary")
    action = decision.get("recommended_next_action") or _dict_at(artifact, "summary").get(
        "recommended_next_step"
    )
    if not action:
        return "Recommendation posture is pending review."
    return f"Recommended next action is {action}."


def _alternatives_summary(artifact: dict[str, Any]) -> str:
    alternatives = _list_at(_dict_at(artifact, "proposal_alternatives"), "alternatives")
    rejected = [
        item for item in alternatives if isinstance(item, dict) and not item.get("selected")
    ]
    if not alternatives:
        return "Proposal alternatives are not available from persisted evidence."
    return f"{len(rejected)} rejected alternatives are available for review."


def _risk_summary(artifact: dict[str, Any]) -> str:
    risk = _dict_at(artifact, "risk_lens")
    return str(risk.get("summary") or "Risk lens evidence is pending review.")


def _approval_summary(artifact: dict[str, Any]) -> str:
    gate = _dict_at(artifact, "gate_decision").get("gate")
    if gate:
        return f"Current proposal gate is {gate}."
    return "Approval and consent posture is pending review."


def _dict_at(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _list_at(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]
