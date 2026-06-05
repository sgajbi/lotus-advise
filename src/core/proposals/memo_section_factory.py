from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.memo_models import (
    ProposalMemoAudience,
    ProposalMemoMaterialClaim,
    ProposalMemoSection,
    ProposalMemoSectionKey,
    ProposalMemoSectionStatus,
    ProposalMemoSourceAuthorityManifest,
)


@dataclass(frozen=True)
class _MemoSectionEvidence:
    source_sections: list[dict[str, Any]]
    missing: list[str]
    reasons: list[str]
    evidence_refs: list[str]
    source_refs: list[str]
    statuses: list[str]


def build_appendix_section(
    section_id: ProposalMemoSectionKey,
    title: str,
    owner_role: str,
    audience_visibility: list[ProposalMemoAudience],
    artifact: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_manifest: ProposalMemoSourceAuthorityManifest,
) -> ProposalMemoSection:
    return build_memo_section(
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
        claims=build_memo_claims(
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


def build_memo_section(
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
    section_evidence = _memo_section_evidence(
        source_sections=source_sections,
        claims=claims,
        forced_missing=forced_missing,
        forced_reasons=forced_reasons,
    )
    status = forced_status or _section_status(
        statuses=section_evidence.statuses,
        missing=section_evidence.missing,
        claims=claims,
    )
    if forced_status == "PENDING_REVIEW" and "BLOCKED" in section_evidence.statuses:
        status = "BLOCKED"
    input_payload = _section_input_payload(
        section_id=section_id,
        artifact=artifact,
        section_evidence=section_evidence,
        claims=claims,
        forced_missing=forced_missing,
        forced_reasons=forced_reasons,
    )
    input_hash = hash_canonical_payload(input_payload)
    section_payload = _section_hash_payload(
        section_id=section_id,
        title=title,
        status=status,
        audience_visibility=audience_visibility,
        summary=summary,
        claims=claims,
        missing=section_evidence.missing,
        reasons=section_evidence.reasons,
        input_hash=input_hash,
    )
    return ProposalMemoSection(
        section_id=section_id,
        title=title,
        status=status,
        audience_visibility=audience_visibility,
        summary=summary,
        material_claims=claims,
        claim_refs=[claim.claim_id for claim in claims],
        evidence_refs=section_evidence.evidence_refs,
        source_authority_refs=section_evidence.source_refs,
        missing_evidence=section_evidence.missing,
        degraded_evidence=_degraded_evidence(section_evidence.source_sections),
        reason_codes=section_evidence.reasons,
        review_required=status != "READY",
        owner_role=owner_role,
        last_material_input_hash=input_hash,
        section_hash=hash_canonical_payload(section_payload),
    )


def build_memo_claims(
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


def _memo_section_evidence(
    *,
    source_sections: list[dict[str, Any]],
    claims: list[ProposalMemoMaterialClaim],
    forced_missing: list[str] | None,
    forced_reasons: list[str] | None,
) -> _MemoSectionEvidence:
    return _MemoSectionEvidence(
        source_sections=source_sections,
        missing=_memo_missing_evidence(source_sections, forced_missing=forced_missing),
        reasons=_memo_reason_codes(source_sections, forced_reasons=forced_reasons),
        evidence_refs=_memo_evidence_refs(source_sections, claims=claims),
        source_refs=_memo_source_refs(source_sections, claims=claims),
        statuses=_memo_source_statuses(source_sections),
    )


def _memo_missing_evidence(
    source_sections: list[dict[str, Any]],
    *,
    forced_missing: list[str] | None,
) -> list[str]:
    return _unique(
        _section_string_values(source_sections, "missing_evidence") + (forced_missing or [])
    )


def _memo_reason_codes(
    source_sections: list[dict[str, Any]],
    *,
    forced_reasons: list[str] | None,
) -> list[str]:
    return _unique(_section_string_values(source_sections, "reason_codes") + (forced_reasons or []))


def _memo_evidence_refs(
    source_sections: list[dict[str, Any]],
    *,
    claims: list[ProposalMemoMaterialClaim],
) -> list[str]:
    return _unique(
        _section_string_values(source_sections, "evidence_refs")
        + [item for claim in claims for item in claim.evidence_refs]
    )


def _memo_source_refs(
    source_sections: list[dict[str, Any]],
    *,
    claims: list[ProposalMemoMaterialClaim],
) -> list[str]:
    return _unique(
        _section_owner_refs(source_sections)
        + [item for claim in claims for item in claim.source_authority_refs]
    )


def _memo_source_statuses(source_sections: list[dict[str, Any]]) -> list[str]:
    return [str(section.get("status")) for section in source_sections]


def _section_string_values(source_sections: list[dict[str, Any]], key: str) -> list[str]:
    return [item for section in source_sections for item in _strings(section.get(key))]


def _section_owner_refs(source_sections: list[dict[str, Any]]) -> list[str]:
    return [
        str(section.get("owner_service"))
        for section in source_sections
        if section.get("owner_service")
    ]


def _section_input_payload(
    *,
    section_id: ProposalMemoSectionKey,
    artifact: dict[str, Any],
    section_evidence: _MemoSectionEvidence,
    claims: list[ProposalMemoMaterialClaim],
    forced_missing: list[str] | None,
    forced_reasons: list[str] | None,
) -> dict[str, Any]:
    return {
        "section_id": section_id,
        "artifact_refs": _section_artifact_refs(section_id, artifact),
        "source_sections": section_evidence.source_sections,
        "claims": [claim.model_dump(mode="json") for claim in claims],
        "forced_missing": forced_missing or [],
        "forced_reasons": forced_reasons or [],
    }


def _section_hash_payload(
    *,
    section_id: ProposalMemoSectionKey,
    title: str,
    status: ProposalMemoSectionStatus,
    audience_visibility: list[ProposalMemoAudience],
    summary: str,
    claims: list[ProposalMemoMaterialClaim],
    missing: list[str],
    reasons: list[str],
    input_hash: str,
) -> dict[str, Any]:
    return {
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


__all__ = [
    "build_appendix_section",
    "build_memo_claims",
    "build_memo_section",
]
