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
from src.core.proposals.memo_section_groups import (
    build_appendix_memo_sections,
    build_foundational_memo_sections,
    build_operational_memo_sections,
    build_policy_review_memo_sections,
)

_MEMO_VERSION = "advisory-proposal-memo-evidence-pack.v1"


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
    return [
        *build_foundational_memo_sections(
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            section_factory=_section,
            claims_factory=_claims,
        ),
        *build_policy_review_memo_sections(
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            section_factory=_section,
        ),
        *build_operational_memo_sections(
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            section_factory=_section,
            claims_factory=_claims,
        ),
        *build_appendix_memo_sections(
            artifact=artifact,
            evidence_bundle=evidence_bundle,
            source_manifest=source_manifest,
            appendix_factory=_appendix,
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
