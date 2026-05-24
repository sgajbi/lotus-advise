from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.memo_models import (
    AdvisoryProposalMemoEvidencePack,
    ProposalMemoAudience,
    ProposalMemoMaterialClaim,
    ProposalMemoSection,
    ProposalMemoSectionKey,
    ProposalMemoSectionStatus,
    ProposalMemoSourceAuthorityManifest,
)
from src.core.proposals.memo_policy_enrichment import (
    build_conflict_disclosure_enrichment,
    build_fee_cost_tax_friction_enrichment,
    build_suitability_best_interest_enrichment,
)

_MEMO_VERSION = "advisory-proposal-memo-evidence-pack.v1"
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


def build_advisory_proposal_memo_evidence_pack(
    *,
    proposal_id: str,
    proposal_version_no: int,
    artifact_json: dict[str, Any],
    evidence_bundle: dict[str, Any],
    proposal_version_id: str | None = None,
) -> AdvisoryProposalMemoEvidencePack:
    """Build a deterministic RFC-0024 memo evidence pack from stored proposal evidence.

    Slice 5 deliberately does not persist, publish, render, archive, or promote the memo. It is a
    pure projection over already persisted proposal evidence and source-readiness posture.
    """

    memo_input = {
        "proposal_id": proposal_id,
        "proposal_version_no": proposal_version_no,
        "proposal_version_id": proposal_version_id,
        "artifact": deepcopy(artifact_json),
        "evidence_bundle": deepcopy(evidence_bundle),
    }
    source_input_hash = hash_canonical_payload(memo_input)
    source_manifest = _build_source_authority_manifest(evidence_bundle)
    sections = _build_sections(
        artifact=artifact_json,
        evidence_bundle=evidence_bundle,
        source_manifest=source_manifest,
    )
    status = _overall_status(sections)
    memo_without_hash = {
        "memo_version": _MEMO_VERSION,
        "proposal_id": proposal_id,
        "proposal_version_no": proposal_version_no,
        "proposal_version_id": proposal_version_id,
        "artifact_id": artifact_json.get("artifact_id"),
        "status": status,
        "projection_policy": _projection_policy(),
        "source_authority_manifest": source_manifest.model_dump(mode="json"),
        "sections": [section.model_dump(mode="json") for section in sections],
        "source_input_hash": source_input_hash,
        "supportability": _supportability(),
    }
    memo_hash = hash_canonical_payload(memo_without_hash)
    memo_id = memo_hash.replace("sha256:", "memo_", 1)[:24]
    return AdvisoryProposalMemoEvidencePack(
        memo_id=memo_id,
        memo_version=_MEMO_VERSION,
        proposal_id=proposal_id,
        proposal_version_no=proposal_version_no,
        proposal_version_id=proposal_version_id,
        artifact_id=_optional_str(artifact_json.get("artifact_id")),
        status=status,
        projection_policy=_projection_policy(),
        source_authority_manifest=source_manifest,
        sections=sections,
        source_input_hash=source_input_hash,
        memo_hash=memo_hash,
        supportability=_supportability(),
    )


def _build_source_authority_manifest(
    evidence_bundle: dict[str, Any],
) -> ProposalMemoSourceAuthorityManifest:
    readiness = _dict_at(evidence_bundle, "memo_source_readiness")
    section_statuses = {
        str(section.get("key")): str(section.get("status"))
        for section in _list_at(readiness, "sections")
        if isinstance(section, dict) and section.get("key") and section.get("status")
    }
    return ProposalMemoSourceAuthorityManifest(
        contract_version=str(readiness.get("contract_version") or "UNKNOWN"),
        overall_posture=str(readiness.get("overall_posture") or "PENDING_REVIEW"),
        source_authority=deepcopy(_dict_at(readiness, "source_authority")),
        section_statuses=section_statuses,
    )


def _build_sections(
    *,
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
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
        _section(
            section_id="EXECUTIVE_SUMMARY",
            title="Executive Summary",
            owner_role="advisor",
            audience_visibility=_ALL_INTERNAL_AUDIENCES,
            source_keys=["advise_decision_summary"],
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            summary=_decision_summary_text(artifact),
            claims=_claims(
                section_id="EXECUTIVE_SUMMARY",
                evidence_refs=["artifact.proposal_decision_summary"],
                source_refs=["lotus-advise:proposal_decision_summary"],
                texts=[_decision_summary_text(artifact)],
                reason_codes=["ADVISE_DECISION_SUMMARY_CAPTURED"],
            ),
        ),
        _section(
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
        _section(
            section_id="ADVISORY_OBJECTIVE_AND_CONSTRAINTS",
            title="Advisory Objective And Constraints",
            owner_role="advisor",
            audience_visibility=_REVIEW_AUDIENCES,
            source_keys=["core_household_account_mandate_objective_restrictions"],
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            summary=_objective_summary(artifact),
            claims=_claims(
                section_id="ADVISORY_OBJECTIVE_AND_CONSTRAINTS",
                evidence_refs=["artifact.summary.objective_tags"],
                source_refs=["lotus-advise:proposal_artifact"],
                texts=[_objective_summary(artifact)],
                reason_codes=["ADVISE_OBJECTIVE_TAGS_CAPTURED"],
            ),
        ),
        _section(
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
            summary=_recommendation_summary(artifact),
            claims=_claims(
                section_id="RECOMMENDATION",
                evidence_refs=[
                    "artifact.proposal_decision_summary",
                    "artifact.summary.recommended_next_step",
                ],
                source_refs=["lotus-advise:proposal_decision_summary"],
                texts=[_recommendation_summary(artifact)],
                reason_codes=["ADVISE_RECOMMENDATION_CAPTURED"],
            ),
        ),
        _section(
            section_id="REJECTED_ALTERNATIVES",
            title="Rejected Alternatives",
            owner_role="investment_desk",
            audience_visibility=_REVIEW_AUDIENCES,
            source_keys=["advise_alternatives_lifecycle_execution_boundary"],
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            summary=_alternatives_summary(artifact),
            claims=_claims(
                section_id="REJECTED_ALTERNATIVES",
                evidence_refs=["artifact.proposal_alternatives.alternatives"],
                source_refs=["lotus-advise:proposal_alternatives"],
                texts=[_alternatives_summary(artifact)],
                reason_codes=["ADVISE_ALTERNATIVES_CAPTURED"],
            ),
        ),
        _section(
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
            claims=_claims(
                section_id="PORTFOLIO_IMPACT",
                evidence_refs=["artifact.portfolio_impact"],
                source_refs=["lotus-core:portfolio_state", "lotus-advise:proposal_artifact"],
                texts=[
                    "Portfolio impact uses the immutable proposal artifact before/after evidence."
                ],
                reason_codes=["PORTFOLIO_IMPACT_CAPTURED"],
            ),
        ),
        _section(
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
            summary=_risk_summary(artifact),
            claims=_claims(
                section_id="RISK_AND_SCENARIO_CONTEXT",
                evidence_refs=["artifact.risk_lens", "evidence_bundle.risk_lens"],
                source_refs=["lotus-risk:risk_lens"],
                texts=[_risk_summary(artifact)],
                reason_codes=["RISK_LENS_CAPTURED"],
            ),
        ),
        _section(
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
        _section(
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
        _section(
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
        _section(
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
            summary=_approval_summary(artifact),
            claims=_claims(
                section_id="APPROVALS_CONSENTS_AND_MAKER_CHECKER",
                evidence_refs=["artifact.gate_decision", "artifact.proposal_decision_summary"],
                source_refs=["lotus-advise:proposal_lifecycle"],
                texts=[_approval_summary(artifact)],
                reason_codes=["APPROVAL_POSTURE_CAPTURED"],
            ),
        ),
        _section(
            section_id="REPORT_ARCHIVE_AND_DELIVERY_READINESS",
            title="Report Archive And Delivery Readiness",
            owner_role="operations",
            audience_visibility=_OPERATIONS_AUDIENCES,
            source_keys=["advise_alternatives_lifecycle_execution_boundary"],
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            summary=(
                "Memo report, render, archive, and delivery readiness is blocked until "
                "later slices."
            ),
            claims=[],
            forced_status="BLOCKED",
            forced_missing=["memo_report_package", "memo_render", "memo_archive_record"],
            forced_reasons=["MEMO_REPORT_RENDER_ARCHIVE_NOT_IMPLEMENTED"],
        ),
        _section(
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
            claims=_claims(
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
        _appendix(
            "EVIDENCE_AND_LINEAGE_APPENDIX",
            "Evidence And Lineage Appendix",
            "audit",
            ["AUDIT", "COMPLIANCE", "OPERATIONS"],
            artifact,
            evidence_bundle,
            source_manifest,
        ),
        _appendix(
            "COMPLIANCE_APPENDIX",
            "Compliance Appendix",
            "compliance_reviewer",
            ["COMPLIANCE", "AUDIT"],
            artifact,
            evidence_bundle,
            source_manifest,
        ),
        _appendix(
            "OPERATIONS_APPENDIX",
            "Operations Appendix",
            "operations",
            ["OPERATIONS", "AUDIT"],
            artifact,
            evidence_bundle,
            source_manifest,
        ),
        _appendix(
            "SUPPORTABILITY_APPENDIX",
            "Supportability Appendix",
            "support",
            ["OPERATIONS", "AUDIT"],
            artifact,
            evidence_bundle,
            source_manifest,
        ),
    ]


def _appendix(
    section_id: ProposalMemoSectionKey,
    title: str,
    owner_role: str,
    audience_visibility: list[ProposalMemoAudience],
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
) -> ProposalMemoSection:
    return _section(
        section_id=section_id,
        title=title,
        owner_role=owner_role,
        audience_visibility=audience_visibility,
        source_keys=list(source_manifest.section_statuses),
        artifact=artifact,
        evidence_bundle=evidence_bundle,
        source_manifest=source_manifest,
        summary=(
            "Appendix section preserving memo evidence, source authority, and "
            "supportability posture."
        ),
        claims=_claims(
            section_id=section_id,
            evidence_refs=["evidence_bundle", "artifact.evidence_bundle"],
            source_refs=list(source_manifest.source_authority),
            texts=[
                "Appendix evidence is derived from immutable proposal evidence and "
                "source-readiness posture."
            ],
            reason_codes=["MEMO_APPENDIX_EVIDENCE_CAPTURED"],
        ),
    )


def _section(
    *,
    section_id: ProposalMemoSectionKey,
    title: str,
    owner_role: str,
    audience_visibility: list[ProposalMemoAudience],
    source_keys: list[str],
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
    summary: str,
    claims: list[ProposalMemoMaterialClaim],
    forced_status: ProposalMemoSectionStatus | None = None,
    forced_missing: list[str] | None = None,
    forced_reasons: list[str] | None = None,
) -> ProposalMemoSection:
    source_sections = _source_sections(evidence_bundle=evidence_bundle, source_keys=source_keys)
    missing = _unique(
        [item for section in source_sections for item in _strings(section.get("missing_evidence"))]
        + (forced_missing or [])
    )
    reasons = _unique(
        [item for section in source_sections for item in _strings(section.get("reason_codes"))]
        + (forced_reasons or [])
    )
    evidence_refs = _unique(
        [item for section in source_sections for item in _strings(section.get("evidence_refs"))]
        + [item for claim in claims for item in claim.evidence_refs]
    )
    source_refs = _unique(
        [
            str(section.get("owner_service"))
            for section in source_sections
            if section.get("owner_service")
        ]
        + [item for claim in claims for item in claim.source_authority_refs]
    )
    statuses = [str(section.get("status")) for section in source_sections]
    status = forced_status or _section_status(statuses=statuses, missing=missing, claims=claims)
    if forced_status == "PENDING_REVIEW" and "BLOCKED" in statuses:
        status = "BLOCKED"
    input_payload = {
        "section_id": section_id,
        "artifact_refs": _section_artifact_refs(section_id, artifact),
        "source_sections": source_sections,
        "claims": [claim.model_dump(mode="json") for claim in claims],
        "forced_missing": forced_missing or [],
        "forced_reasons": forced_reasons or [],
    }
    input_hash = hash_canonical_payload(input_payload)
    section_payload = {
        "section_id": section_id,
        "title": title,
        "status": status,
        "audience_visibility": audience_visibility,
        "summary": summary,
        "claims": [claim.model_dump(mode="json") for claim in claims],
        "missing_evidence": missing,
        "reason_codes": reasons,
        "input_hash": input_hash,
    }
    return ProposalMemoSection(
        section_id=section_id,
        title=title,
        status=status,
        audience_visibility=audience_visibility,
        summary=summary,
        material_claims=claims,
        claim_refs=[claim.claim_id for claim in claims],
        evidence_refs=evidence_refs,
        source_authority_refs=source_refs,
        missing_evidence=missing,
        degraded_evidence=_degraded_evidence(source_sections),
        reason_codes=reasons,
        review_required=status != "READY",
        owner_role=owner_role,
        last_material_input_hash=input_hash,
        section_hash=hash_canonical_payload(section_payload),
    )


def _claims(
    *,
    section_id: str,
    evidence_refs: list[str],
    source_refs: list[str],
    texts: list[str],
    reason_codes: list[str],
) -> list[ProposalMemoMaterialClaim]:
    if not evidence_refs or not source_refs:
        return []
    claims = []
    for index, text in enumerate(text for text in texts if text):
        claims.append(
            ProposalMemoMaterialClaim(
                claim_id=f"{section_id.lower()}.claim.{index + 1}",
                text=text,
                evidence_refs=evidence_refs,
                source_authority_refs=source_refs,
                reason_codes=reason_codes,
            )
        )
    return claims


def _source_sections(
    *, evidence_bundle: dict[str, Any], source_keys: list[str]
) -> list[dict[str, Any]]:
    sections = _list_at(_dict_at(evidence_bundle, "memo_source_readiness"), "sections")
    return [
        deepcopy(section)
        for section in sections
        if isinstance(section, dict) and section.get("key") in source_keys
    ]


def _section_status(
    *, statuses: list[str], missing: list[str], claims: list[ProposalMemoMaterialClaim]
) -> ProposalMemoSectionStatus:
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if "PENDING_REVIEW" in statuses or "NOT_AVAILABLE" in statuses or missing:
        return "PENDING_REVIEW"
    if claims:
        return "READY"
    return "PENDING_REVIEW"


def _overall_status(sections: list[ProposalMemoSection]) -> ProposalMemoSectionStatus:
    statuses = {section.status for section in sections}
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if "PENDING_REVIEW" in statuses:
        return "PENDING_REVIEW"
    return "READY"


def _projection_policy() -> dict[str, Any]:
    return {
        "advisor_projection": "SUPPORTED_BY_PURE_BUILDER",
        "client_draft_projection": "BLOCKED_UNTIL_POLICY_REDACTION_AND_REVIEW",
        "client_ready_publication": "BLOCKED",
        "report_render_archive": "BLOCKED_UNTIL_LATER_RFC0024_SLICES",
    }


def _supportability() -> dict[str, Any]:
    return {
        "capability_posture": "ADVISE_MEMO_EVIDENCE_PACK_SUPPORTED_INTERNAL",
        "persistence": "SUPPORTED_BY_RFC0024_SLICE6",
        "api": "SUPPORTED_BY_RFC0024_SLICE7",
        "policy_fee_conflict_enrichment": "SUPPORTED_BY_RFC0024_SLICE8",
        "memo_generation": "DETERMINISTIC_SOURCE_EVIDENCE_PROJECTION",
        "report_render_archive": "NOT_IMPLEMENTED",
        "client_ready_publication": "BLOCKED",
    }


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


def _section_artifact_refs(section_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
    section_ref_map = {
        "EXECUTIVE_SUMMARY": ["proposal_decision_summary"],
        "RECOMMENDATION": ["proposal_decision_summary", "summary"],
        "REJECTED_ALTERNATIVES": ["proposal_alternatives"],
        "PORTFOLIO_IMPACT": ["portfolio_impact"],
        "RISK_AND_SCENARIO_CONTEXT": ["risk_lens"],
        "SUITABILITY_AND_BEST_INTEREST": ["suitability_summary", "proposal_decision_summary"],
        "APPROVALS_CONSENTS_AND_MAKER_CHECKER": ["gate_decision", "proposal_decision_summary"],
        "EXECUTION_HANDOFF_BOUNDARY": ["trades_and_funding"],
    }
    return {key: deepcopy(artifact.get(key)) for key in section_ref_map.get(section_id, [])}


def _degraded_evidence(source_sections: list[dict[str, Any]]) -> list[str]:
    degraded = []
    for section in source_sections:
        status = section.get("status")
        if status == "PENDING_REVIEW":
            degraded.append(str(section.get("key")))
    return _unique(degraded)


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


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
