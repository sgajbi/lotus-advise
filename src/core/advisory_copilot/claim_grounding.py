from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.advisory_copilot.packet_models import CopilotEvidencePacket
from src.core.advisory_copilot.reference_models import CopilotSourceRef

COPILOT_CLAIM_LIMIT_PER_SECTION = 8
COPILOT_CLAIM_SOURCE_REF_LIMIT = 8
COPILOT_CLAIM_ID_MAX_LENGTH = 96
COPILOT_CLAIM_TEXT_MAX_LENGTH = 1000
COPILOT_CLAIM_REASON_MAX_LENGTH = 160

GROUNDING_STATUS_GROUNDED = "GROUNDED"
GROUNDING_STATUS_PARTIAL = "PARTIAL"
GROUNDING_STATUS_UNSUPPORTED = "UNSUPPORTED"
GROUNDING_STATUS_UNVERIFIABLE = "UNVERIFIABLE"

REASON_CLAIM_REFS_MISSING = "COPILOT_CLAIM_REFS_MISSING"
REASON_CLAIM_SOURCE_REFS_MISSING = "COPILOT_CLAIM_SOURCE_REFS_MISSING"
REASON_CLAIM_SOURCE_REF_UNKNOWN = "COPILOT_CLAIM_SOURCE_REF_UNKNOWN"
REASON_CLAIM_SOURCE_REF_SECTION_MISMATCH = "COPILOT_CLAIM_SOURCE_REF_SECTION_MISMATCH"
REASON_CLAIM_ID_DUPLICATE = "COPILOT_CLAIM_ID_DUPLICATE"
REASON_CLAIM_UNSUPPORTED_BY_PROVIDER = "COPILOT_CLAIM_UNSUPPORTED_BY_PROVIDER"


@dataclass(frozen=True)
class CopilotClaimEvidencePosture:
    source_refs: tuple[str, ...]
    unsupported_reason: str | None
    duplicate: bool
    unknown_refs: tuple[str, ...]
    section_mismatch_refs: tuple[str, ...]
    grounding_status: str
    reason: str | None


def copilot_source_ref_identity(source_ref: CopilotSourceRef) -> str:
    return ":".join(
        (
            source_ref.source_system,
            source_ref.source_type,
            source_ref.source_id,
            source_ref.content_hash or "no-content-hash",
        )
    )


def align_copilot_output_claims_to_evidence(
    *,
    evidence_packet: CopilotEvidencePacket,
    raw_sections: Any,
    output_sections: tuple[dict[str, Any], ...],
) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    packet_refs, section_refs = _source_ref_indexes(evidence_packet)
    raw_section_by_key = _raw_section_index(raw_sections)
    seen_claim_ids: set[str] = set()
    grounded_sections: list[dict[str, Any]] = []
    total_claims = 0
    grounded_claims = 0
    unsupported_claims = 0
    unverifiable_claims = 0
    unknown_source_refs: set[str] = set()

    for section in output_sections:
        section_key = str(section.get("section_key") or "")
        raw_section = raw_section_by_key.get(section_key, {})
        claim_grounding = _claim_grounding_for_section(
            raw_section=raw_section,
            section_key=section_key,
            packet_refs=packet_refs,
            section_refs=section_refs.get(section_key, set()),
            seen_claim_ids=seen_claim_ids,
        )
        total_claims += len(claim_grounding)
        grounded_claims += _count_claims(claim_grounding, GROUNDING_STATUS_GROUNDED)
        unsupported_claims += _count_claims(claim_grounding, GROUNDING_STATUS_UNSUPPORTED)
        unverifiable_claims += _count_claims(claim_grounding, GROUNDING_STATUS_UNVERIFIABLE)
        unknown_source_refs.update(
            ref
            for claim in claim_grounding
            for ref in claim.get("unknown_source_refs", ())
            if isinstance(ref, str)
        )
        section_status = _section_grounding_status(claim_grounding)
        grounded_section = dict(section)
        grounded_section["grounding_status"] = section_status
        grounded_section["claim_grounding"] = claim_grounding
        if section_status != GROUNDING_STATUS_GROUNDED:
            grounded_section["review_state"] = "UNSUPPORTED"
        grounded_sections.append(grounded_section)

    ready_for_review = (
        bool(output_sections) and total_claims > 0 and (total_claims == grounded_claims)
    )
    return tuple(grounded_sections), {
        "grounding_status": (
            GROUNDING_STATUS_GROUNDED if ready_for_review else GROUNDING_STATUS_UNSUPPORTED
        ),
        "ready_for_review": ready_for_review,
        "total_sections": len(output_sections),
        "total_claims": total_claims,
        "grounded_claims": grounded_claims,
        "unsupported_claims": unsupported_claims,
        "unverifiable_claims": unverifiable_claims,
        "unknown_source_refs": sorted(unknown_source_refs),
    }


def _source_ref_indexes(
    evidence_packet: CopilotEvidencePacket,
) -> tuple[set[str], dict[str, set[str]]]:
    packet_refs: set[str] = set()
    section_refs: dict[str, set[str]] = {}
    for section in evidence_packet.sections:
        refs = {copilot_source_ref_identity(source_ref) for source_ref in section.source_refs}
        packet_refs.update(refs)
        section_refs[section.section_key] = refs
    return packet_refs, section_refs


def _raw_section_index(raw_sections: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw_sections, list):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for raw_section in raw_sections:
        if not isinstance(raw_section, dict):
            continue
        section_key = _bounded_text(
            raw_section.get("section_key"),
            max_length=COPILOT_CLAIM_ID_MAX_LENGTH,
        )
        if section_key and section_key not in indexed:
            indexed[section_key] = raw_section
    return indexed


def _claim_grounding_for_section(
    *,
    raw_section: dict[str, Any],
    section_key: str,
    packet_refs: set[str],
    section_refs: set[str],
    seen_claim_ids: set[str],
) -> tuple[dict[str, Any], ...]:
    claims = _raw_claims(raw_section=raw_section, section_key=section_key)
    if not claims:
        return (
            {
                "claim_id": section_key or "section",
                "grounding_status": GROUNDING_STATUS_UNSUPPORTED,
                "source_refs": (),
                "unsupported_reason": REASON_CLAIM_REFS_MISSING,
            },
        )
    return tuple(
        _ground_claim(
            claim=claim,
            section_key=section_key,
            packet_refs=packet_refs,
            section_refs=section_refs,
            seen_claim_ids=seen_claim_ids,
        )
        for claim in claims[:COPILOT_CLAIM_LIMIT_PER_SECTION]
    )


def _raw_claims(*, raw_section: dict[str, Any], section_key: str) -> list[dict[str, Any]]:
    claims = raw_section.get("claims")
    if isinstance(claims, list):
        return [claim for claim in claims if isinstance(claim, dict)]
    section_source_refs = raw_section.get("source_refs")
    if isinstance(section_source_refs, list):
        return [
            {
                "claim_id": section_key,
                "claim_text": raw_section.get("text"),
                "source_refs": section_source_refs,
            }
        ]
    return []


def _ground_claim(
    *,
    claim: dict[str, Any],
    section_key: str,
    packet_refs: set[str],
    section_refs: set[str],
    seen_claim_ids: set[str],
) -> dict[str, Any]:
    claim_id = _claim_id(claim=claim, section_key=section_key)
    claim_text = _bounded_text(
        claim.get("claim_text") or claim.get("text"),
        max_length=COPILOT_CLAIM_TEXT_MAX_LENGTH,
    )
    evidence_posture = _claim_evidence_posture(
        claim=claim,
        claim_id=claim_id,
        packet_refs=packet_refs,
        section_refs=section_refs,
        seen_claim_ids=seen_claim_ids,
    )
    return _claim_grounding_record(
        claim_id=claim_id,
        claim_text=claim_text,
        evidence_posture=evidence_posture,
    )


def _claim_evidence_posture(
    *,
    claim: dict[str, Any],
    claim_id: str,
    packet_refs: set[str],
    section_refs: set[str],
    seen_claim_ids: set[str],
) -> CopilotClaimEvidencePosture:
    source_refs = _bounded_source_refs(claim.get("source_refs"))
    unsupported_reason = _bounded_text(
        claim.get("unsupported_reason"),
        max_length=COPILOT_CLAIM_REASON_MAX_LENGTH,
    )
    duplicate = claim_id in seen_claim_ids
    seen_claim_ids.add(claim_id)
    unknown_refs = tuple(ref for ref in source_refs if ref not in packet_refs)
    section_mismatch_refs = tuple(
        ref for ref in source_refs if ref in packet_refs and ref not in section_refs
    )
    grounding_status, reason = _claim_status(
        source_refs=source_refs,
        unsupported_reason=unsupported_reason,
        duplicate=duplicate,
        unknown_refs=unknown_refs,
        section_mismatch_refs=section_mismatch_refs,
    )
    return CopilotClaimEvidencePosture(
        source_refs=source_refs,
        unsupported_reason=unsupported_reason,
        duplicate=duplicate,
        unknown_refs=unknown_refs,
        section_mismatch_refs=section_mismatch_refs,
        grounding_status=grounding_status,
        reason=reason,
    )


def _claim_grounding_record(
    *,
    claim_id: str,
    claim_text: str | None,
    evidence_posture: CopilotClaimEvidencePosture,
) -> dict[str, Any]:
    grounded: dict[str, Any] = {
        "claim_id": claim_id,
        "grounding_status": evidence_posture.grounding_status,
        "source_refs": evidence_posture.source_refs,
    }
    if claim_text:
        grounded["claim_text"] = claim_text
    if evidence_posture.reason:
        grounded["unsupported_reason"] = evidence_posture.reason
    if evidence_posture.unknown_refs:
        grounded["unknown_source_refs"] = evidence_posture.unknown_refs
    if evidence_posture.section_mismatch_refs:
        grounded["section_mismatch_source_refs"] = evidence_posture.section_mismatch_refs
    return grounded


def _claim_id(*, claim: dict[str, Any], section_key: str) -> str:
    candidate = _bounded_text(
        claim.get("claim_id"),
        max_length=COPILOT_CLAIM_ID_MAX_LENGTH,
    )
    if candidate:
        return candidate
    return section_key or "section"


def _bounded_source_refs(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    refs: list[str] = []
    seen: set[str] = set()
    for item in value:
        ref = _bounded_text(str(item), max_length=512)
        if not ref or ref in seen:
            continue
        refs.append(ref)
        seen.add(ref)
        if len(refs) >= COPILOT_CLAIM_SOURCE_REF_LIMIT:
            break
    return tuple(refs)


def _claim_status(
    *,
    source_refs: tuple[str, ...],
    unsupported_reason: str | None,
    duplicate: bool,
    unknown_refs: tuple[str, ...],
    section_mismatch_refs: tuple[str, ...],
) -> tuple[str, str | None]:
    if duplicate:
        return GROUNDING_STATUS_UNVERIFIABLE, REASON_CLAIM_ID_DUPLICATE
    if unknown_refs:
        return GROUNDING_STATUS_UNVERIFIABLE, REASON_CLAIM_SOURCE_REF_UNKNOWN
    if section_mismatch_refs:
        return GROUNDING_STATUS_UNVERIFIABLE, REASON_CLAIM_SOURCE_REF_SECTION_MISMATCH
    if source_refs:
        return GROUNDING_STATUS_GROUNDED, None
    if unsupported_reason:
        return GROUNDING_STATUS_UNSUPPORTED, unsupported_reason
    return GROUNDING_STATUS_UNSUPPORTED, REASON_CLAIM_SOURCE_REFS_MISSING


def _section_grounding_status(claim_grounding: tuple[dict[str, Any], ...]) -> str:
    statuses = {str(claim.get("grounding_status")) for claim in claim_grounding}
    if statuses == {GROUNDING_STATUS_GROUNDED}:
        return GROUNDING_STATUS_GROUNDED
    if GROUNDING_STATUS_GROUNDED in statuses:
        return GROUNDING_STATUS_PARTIAL
    if GROUNDING_STATUS_UNVERIFIABLE in statuses:
        return GROUNDING_STATUS_UNVERIFIABLE
    return GROUNDING_STATUS_UNSUPPORTED


def _count_claims(claim_grounding: tuple[dict[str, Any], ...], status: str) -> int:
    return sum(1 for claim in claim_grounding if claim.get("grounding_status") == status)


def _bounded_text(value: Any, *, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = " ".join(value.split())
    if not stripped or len(stripped) > max_length:
        return None
    return stripped
