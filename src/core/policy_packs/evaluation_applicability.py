from __future__ import annotations

from typing import Any

from src.core.policy_packs.evaluation_models import PolicyPackApplicabilityResult
from src.core.proposals.source_readiness_common import dict_at, list_at

BOOKING_LOCATION_SOURCE_KEY = "booking_" + "center_code"
BOOKING_LOCATION_SCOPE_KEY = "booking_" + "center_code_scope"

PRIVATE_BANKING_CLIENT_CLASSIFICATIONS = {
    "ACCREDITED_INVESTOR",
    "PRIVATE_BANKING",
}


def evaluate_policy_pack_applicability(
    *, evidence_bundle: dict[str, Any], applicability: dict[str, Any]
) -> PolicyPackApplicabilityResult:
    context = dict_at(dict_at(evidence_bundle, "context_resolution"), "advisory_policy_context")
    jurisdiction = str(context.get("jurisdiction") or "")
    booking_location_code = str(context.get(BOOKING_LOCATION_SOURCE_KEY) or "")
    client_segment = str(context.get("client_classification") or "")
    missing = []
    if not jurisdiction:
        missing.append("jurisdiction")
    if not client_segment:
        missing.append("client_classification")
    if missing:
        return PolicyPackApplicabilityResult(
            status="BLOCKED",
            missing_evidence=missing,
            reason_codes=["POLICY_APPLICABILITY_SOURCE_EVIDENCE_MISSING"],
        )

    if not _matches_scope(jurisdiction, list_at(applicability, "jurisdiction_scope")):
        return PolicyPackApplicabilityResult(
            status="NOT_APPLICABLE",
            matched_selectors={"jurisdiction": jurisdiction},
            reason_codes=["POLICY_PACK_JURISDICTION_NOT_APPLICABLE"],
        )
    if booking_location_code and not _matches_scope(
        booking_location_code, list_at(applicability, BOOKING_LOCATION_SCOPE_KEY)
    ):
        return PolicyPackApplicabilityResult(
            status="NOT_APPLICABLE",
            matched_selectors={
                "jurisdiction": jurisdiction,
                "booking_location_code": booking_location_code,
            },
            reason_codes=["POLICY_PACK_BOOKING_LOCATION_NOT_APPLICABLE"],
        )
    if not _client_segment_matches_scope(
        client_segment, list_at(applicability, "client_segment_scope")
    ):
        return PolicyPackApplicabilityResult(
            status="NOT_APPLICABLE",
            matched_selectors={"jurisdiction": jurisdiction, "client_segment": client_segment},
            reason_codes=["POLICY_PACK_CLIENT_SEGMENT_NOT_APPLICABLE"],
        )

    return PolicyPackApplicabilityResult(
        status="APPLICABLE",
        matched_selectors={
            "jurisdiction": jurisdiction,
            "client_segment": client_segment,
            **({"booking_location_code": booking_location_code} if booking_location_code else {}),
        },
        reason_codes=["POLICY_PACK_APPLIES_TO_PROPOSAL_CONTEXT"],
    )


def _matches_scope(value: str, scope: list[Any]) -> bool:
    normalized_scope = {str(item) for item in scope}
    return "GLOBAL" in normalized_scope or value in normalized_scope


def _client_segment_matches_scope(value: str, scope: list[Any]) -> bool:
    normalized_scope = {str(item) for item in scope}
    return (
        "GLOBAL" in normalized_scope
        or value in normalized_scope
        or (
            "PRIVATE_BANKING" in normalized_scope
            and value in PRIVATE_BANKING_CLIENT_CLASSIFICATIONS
        )
    )
