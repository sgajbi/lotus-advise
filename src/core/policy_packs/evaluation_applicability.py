from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.policy_packs.evaluation_models import PolicyPackApplicabilityResult
from src.core.policy_packs.evaluation_product_helpers import (
    policy_product_scopes,
    proposed_shelf_rows,
)
from src.core.proposals.source_readiness_common import dict_at, list_at

BOOKING_LOCATION_SOURCE_KEY = "booking_" + "center_code"
BOOKING_LOCATION_SCOPE_KEY = "booking_" + "center_code_scope"
LEGAL_ENTITY_SOURCE_KEY = "legal_entity_code"
LEGAL_ENTITY_SCOPE_KEY = "legal_entity_scope"
PRODUCT_SCOPE_KEY = "product_scope"

PRIVATE_BANKING_CLIENT_CLASSIFICATIONS = {
    "ACCREDITED_INVESTOR",
    "PRIVATE_BANKING",
}

_MISSING_REASON_CODES = {
    "jurisdiction": "POLICY_APPLICABILITY_JURISDICTION_SOURCE_MISSING",
    BOOKING_LOCATION_SOURCE_KEY: "POLICY_APPLICABILITY_BOOKING_LOCATION_SOURCE_MISSING",
    LEGAL_ENTITY_SOURCE_KEY: "POLICY_APPLICABILITY_LEGAL_ENTITY_SOURCE_MISSING",
    "client_classification": "POLICY_APPLICABILITY_CLIENT_SEGMENT_SOURCE_MISSING",
    PRODUCT_SCOPE_KEY: "POLICY_APPLICABILITY_PRODUCT_SCOPE_SOURCE_MISSING",
}


@dataclass(frozen=True)
class ApplicabilitySelectorRequirement:
    scope_key: str
    evidence_key: str
    context_value: str | tuple[str, ...]


@dataclass(frozen=True)
class PolicyApplicabilityContext:
    jurisdiction: str
    booking_location_code: str
    legal_entity_code: str
    client_segment: str
    product_scopes: tuple[str, ...]

    def matched_selectors(self) -> dict[str, str]:
        selectors = {
            "jurisdiction": self.jurisdiction,
            "client_segment": self.client_segment,
        }
        if self.booking_location_code:
            selectors["booking_center_code"] = self.booking_location_code
        if self.legal_entity_code:
            selectors[LEGAL_ENTITY_SOURCE_KEY] = self.legal_entity_code
        if self.product_scopes:
            selectors[PRODUCT_SCOPE_KEY] = "|".join(self.product_scopes)
        return selectors


def evaluate_policy_pack_applicability(
    *, evidence_bundle: dict[str, Any], applicability: dict[str, Any]
) -> PolicyPackApplicabilityResult:
    context = _applicability_context(evidence_bundle)
    missing = _missing_applicability_evidence(context=context, applicability=applicability)
    if missing:
        return PolicyPackApplicabilityResult(
            status="BLOCKED",
            missing_evidence=missing,
            reason_codes=_missing_reason_codes(missing),
        )

    if not _matches_scope(context.jurisdiction, list_at(applicability, "jurisdiction_scope")):
        return _not_applicable_result(
            matched_selectors={"jurisdiction": context.jurisdiction},
            reason_code="POLICY_PACK_JURISDICTION_NOT_APPLICABLE",
        )
    if context.booking_location_code and not _matches_scope(
        context.booking_location_code, list_at(applicability, BOOKING_LOCATION_SCOPE_KEY)
    ):
        return _not_applicable_result(
            matched_selectors=context.matched_selectors(),
            reason_code="POLICY_PACK_BOOKING_LOCATION_NOT_APPLICABLE",
        )
    if context.legal_entity_code and not _matches_scope(
        context.legal_entity_code, list_at(applicability, LEGAL_ENTITY_SCOPE_KEY)
    ):
        return _not_applicable_result(
            matched_selectors=context.matched_selectors(),
            reason_code="POLICY_PACK_LEGAL_ENTITY_NOT_APPLICABLE",
        )
    if not _client_segment_matches_scope(
        context.client_segment, list_at(applicability, "client_segment_scope")
    ):
        return _not_applicable_result(
            matched_selectors=context.matched_selectors(),
            reason_code="POLICY_PACK_CLIENT_SEGMENT_NOT_APPLICABLE",
        )
    if not _product_scope_matches_scope(
        context.product_scopes, list_at(applicability, PRODUCT_SCOPE_KEY)
    ):
        return _not_applicable_result(
            matched_selectors=context.matched_selectors(),
            reason_code="POLICY_PACK_PRODUCT_SCOPE_NOT_APPLICABLE",
        )

    return PolicyPackApplicabilityResult(
        status="APPLICABLE",
        matched_selectors=context.matched_selectors(),
        reason_codes=["POLICY_PACK_APPLIES_TO_PROPOSAL_CONTEXT"],
    )


def _applicability_context(evidence_bundle: dict[str, Any]) -> PolicyApplicabilityContext:
    context = dict_at(dict_at(evidence_bundle, "context_resolution"), "advisory_policy_context")
    return PolicyApplicabilityContext(
        jurisdiction=_normalized_selector(context.get("jurisdiction")),
        booking_location_code=_normalized_selector(context.get(BOOKING_LOCATION_SOURCE_KEY)),
        legal_entity_code=_normalized_selector(context.get(LEGAL_ENTITY_SOURCE_KEY)),
        client_segment=_normalized_selector(context.get("client_classification")),
        product_scopes=_product_scopes(evidence_bundle),
    )


def _missing_applicability_evidence(
    *, context: PolicyApplicabilityContext, applicability: dict[str, Any]
) -> list[str]:
    return [
        requirement.evidence_key
        for requirement in _selector_requirements(context)
        if _requires_selector(applicability, requirement.scope_key)
        and not requirement.context_value
    ]


def _selector_requirements(
    context: PolicyApplicabilityContext,
) -> tuple[ApplicabilitySelectorRequirement, ...]:
    return (
        ApplicabilitySelectorRequirement(
            scope_key="jurisdiction_scope",
            evidence_key="jurisdiction",
            context_value=context.jurisdiction,
        ),
        ApplicabilitySelectorRequirement(
            scope_key=BOOKING_LOCATION_SCOPE_KEY,
            evidence_key=BOOKING_LOCATION_SOURCE_KEY,
            context_value=context.booking_location_code,
        ),
        ApplicabilitySelectorRequirement(
            scope_key=LEGAL_ENTITY_SCOPE_KEY,
            evidence_key=LEGAL_ENTITY_SOURCE_KEY,
            context_value=context.legal_entity_code,
        ),
        ApplicabilitySelectorRequirement(
            scope_key="client_segment_scope",
            evidence_key="client_classification",
            context_value=context.client_segment,
        ),
        ApplicabilitySelectorRequirement(
            scope_key=PRODUCT_SCOPE_KEY,
            evidence_key=PRODUCT_SCOPE_KEY,
            context_value=context.product_scopes,
        ),
    )


def _missing_reason_codes(missing: list[str]) -> list[str]:
    return ["POLICY_APPLICABILITY_SOURCE_EVIDENCE_MISSING"] + [
        _MISSING_REASON_CODES[item] for item in missing if item in _MISSING_REASON_CODES
    ]


def _not_applicable_result(
    *, matched_selectors: dict[str, str], reason_code: str
) -> PolicyPackApplicabilityResult:
    return PolicyPackApplicabilityResult(
        status="NOT_APPLICABLE",
        matched_selectors={key: value for key, value in matched_selectors.items() if value},
        reason_codes=[reason_code],
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


def _product_scope_matches_scope(product_scopes: tuple[str, ...], scope: list[Any]) -> bool:
    normalized_scope = {str(item) for item in scope}
    if "GLOBAL" in normalized_scope:
        return True
    return bool(set(product_scopes).intersection(normalized_scope))


def _requires_selector(applicability: dict[str, Any], scope_key: str) -> bool:
    scope = {str(item) for item in list_at(applicability, scope_key)}
    return bool(scope) and "GLOBAL" not in scope


def _product_scopes(evidence_bundle: dict[str, Any]) -> tuple[str, ...]:
    scopes: set[str] = set()
    for shelf in proposed_shelf_rows(evidence_bundle).values():
        if shelf is not None:
            scopes.update(policy_product_scopes(shelf))
    return tuple(sorted(scopes))


def _normalized_selector(value: Any) -> str:
    return str(value).strip().upper() if value is not None and str(value).strip() else ""
