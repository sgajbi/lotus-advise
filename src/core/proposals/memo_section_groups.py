from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.core.proposals.memo_foundational_sections import (
    build_foundational_memo_sections as build_foundational_memo_sections,
)
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


def _approval_summary(artifact: dict[str, Any]) -> str:
    gate = _dict_at(artifact, "gate_decision").get("gate")
    if gate:
        return f"Current proposal gate is {gate}."
    return "Approval and consent posture is pending review."


def _dict_at(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}
