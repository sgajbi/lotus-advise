from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.core.advisory.artifact_models import ProposalArtifact
from src.core.advisory.narrative_policy_models import (
    ProposalNarrativeDisclosure,
    ProposalNarrativeGuardrailResult,
    ProposalNarrativePolicy,
    ProposalNarrativePolicyContext,
)
from src.core.advisory.narrative_request_models import ProposalNarrativeRequest
from src.core.advisory.narrative_section_models import ProposalNarrativeSection
from src.core.advisory.narrative_types import (
    ProposalNarrativeClientAudience,
    ProposalNarrativeRiskPosture,
)

NARRATIVE_POLICY_VERSION = "advisory-narrative-policy.2026-05"
SUPPORTED_DISCLOSURE_JURISDICTIONS = frozenset({"SG", "US"})
PROHIBITED_CLAIM_PATTERNS = (
    "guaranteed return",
    "risk-free",
    "suitable for all clients",
    "tax advice",
    "approved for client distribution",
)
ASSET_CLASS_PRODUCT_TYPES = {
    "EQUITY": "EQUITY",
    "EQUITIES": "EQUITY",
    "FX": "FX",
    "FOREIGN_EXCHANGE": "FX",
    "CASH": "CASH",
    "CASH_EQUIVALENT": "CASH",
}
UNSPECIFIED_ASSET_CLASSES = frozenset({"UNSPECIFIED", "UNKNOWN"})


@dataclass(frozen=True)
class _DisclosureRule:
    disclosure_id: str
    jurisdiction: str
    product_type: str
    text: str


_DISCLOSURE_RULES: tuple[_DisclosureRule, ...] = (
    _DisclosureRule(
        disclosure_id="DISC_SG_GENERAL_MARKET_RISK",
        jurisdiction="SG",
        product_type="ALL",
        text=(
            "Investments are subject to market risk, liquidity risk, and price movements; "
            "past performance is not a reliable indicator of future performance."
        ),
    ),
    _DisclosureRule(
        disclosure_id="DISC_SG_EQUITY_PRODUCT_RISK",
        jurisdiction="SG",
        product_type="EQUITY",
        text=(
            "Equity and equity-linked exposures may fluctuate materially and may not be suitable "
            "where the mandate or risk budget cannot absorb capital volatility."
        ),
    ),
    _DisclosureRule(
        disclosure_id="DISC_SG_FX_EXECUTION_RISK",
        jurisdiction="SG",
        product_type="FX",
        text=(
            "Foreign-exchange conversion is subject to execution timing, spread, and settlement "
            "risk."
        ),
    ),
    _DisclosureRule(
        disclosure_id="DISC_SG_CONCENTRATION_REVIEW",
        jurisdiction="SG",
        product_type="CONCENTRATION_REVIEW",
        text=(
            "The proposal should be reviewed for single-name, issuer, sector, and portfolio "
            "concentration effects before client distribution."
        ),
    ),
    _DisclosureRule(
        disclosure_id="DISC_US_GENERAL_MARKET_RISK",
        jurisdiction="US",
        product_type="ALL",
        text=(
            "Investment recommendations are subject to market, liquidity, and suitability risk; "
            "portfolio outcomes are not assured."
        ),
    ),
    _DisclosureRule(
        disclosure_id="DISC_US_EQUITY_PRODUCT_RISK",
        jurisdiction="US",
        product_type="EQUITY",
        text=(
            "Equity exposures can lose value and require suitability and concentration review "
            "before client distribution."
        ),
    ),
)


def normalize_policy_token(value: str | None) -> str:
    normalized = (value or "").strip().upper().replace("-", "_").replace(" ", "_")
    return normalized or "UNSPECIFIED"


def is_disclosure_policy_available(jurisdiction: str | None) -> bool:
    return normalize_policy_token(jurisdiction) in SUPPORTED_DISCLOSURE_JURISDICTIONS


def _product_type_from_asset_class(asset_class: str | None) -> str | None:
    normalized = normalize_policy_token(asset_class)
    if normalized in UNSPECIFIED_ASSET_CLASSES:
        return None
    return ASSET_CLASS_PRODUCT_TYPES.get(normalized, normalized)


def _iter_evidence_product_types(artifact: ProposalArtifact) -> Iterable[str]:
    for shelf_entry in artifact.evidence_bundle.inputs.shelf_entries:
        yield from _iter_shelf_entry_product_types(shelf_entry)
    if artifact.trades_and_funding.fx_list:
        yield "FX"


def _iter_shelf_entry_product_types(shelf_entry: object) -> Iterable[str]:
    if not isinstance(shelf_entry, dict):
        return
    if product_type := _shelf_entry_attribute_product_type(shelf_entry):
        yield product_type
    if product_type := _shelf_entry_asset_class_product_type(shelf_entry):
        yield product_type


def _shelf_entry_attribute_product_type(shelf_entry: dict[str, object]) -> str | None:
    attributes = shelf_entry.get("attributes")
    if not isinstance(attributes, dict):
        return None
    product_type = attributes.get("product_type")
    return product_type if isinstance(product_type, str) else None


def _shelf_entry_asset_class_product_type(shelf_entry: dict[str, object]) -> str | None:
    asset_class = shelf_entry.get("asset_class")
    if not isinstance(asset_class, str):
        return None
    return _product_type_from_asset_class(asset_class)


def resolve_narrative_product_types(
    *, artifact: ProposalArtifact, request: ProposalNarrativeRequest
) -> list[str]:
    product_types = sorted(
        _usable_policy_tokens((*request.product_types, *_iter_evidence_product_types(artifact)))
    )
    return product_types or ["UNKNOWN"]


def _usable_policy_tokens(items: Iterable[str]) -> set[str]:
    return {
        normalized
        for item in items
        if (normalized := normalize_policy_token(item)) != "UNSPECIFIED"
    }


def resolve_narrative_risk_posture(artifact: ProposalArtifact) -> ProposalNarrativeRiskPosture:
    if artifact.risk_lens.status != "AVAILABLE":
        return "UNAVAILABLE"
    risk_text = " ".join([artifact.risk_lens.summary, *artifact.risk_lens.highlights]).lower()
    if any(token in risk_text for token in ("increase", "concentration", "issuer", "single")):
        return "CONCENTRATION_REVIEW"
    if artifact.suitability_summary.highest_severity_new in {"MEDIUM", "HIGH"}:
        return "CONCENTRATION_REVIEW"
    return "STANDARD"


def _select_disclosures(
    *,
    jurisdiction: str,
    product_types: list[str],
    risk_posture: ProposalNarrativeRiskPosture,
    required_for: ProposalNarrativeClientAudience,
) -> list[ProposalNarrativeDisclosure]:
    if jurisdiction not in SUPPORTED_DISCLOSURE_JURISDICTIONS:
        return []

    disclosure_keys = {"ALL", *product_types}
    if risk_posture == "CONCENTRATION_REVIEW":
        disclosure_keys.add("CONCENTRATION_REVIEW")

    return [
        _disclosure_from_rule(rule, required_for=required_for)
        for rule in _DISCLOSURE_RULES
        if _rule_matches_disclosure_keys(
            rule,
            jurisdiction=jurisdiction,
            disclosure_keys=disclosure_keys,
        )
    ]


def _rule_matches_disclosure_keys(
    rule: _DisclosureRule, *, jurisdiction: str, disclosure_keys: set[str]
) -> bool:
    return rule.jurisdiction == jurisdiction and rule.product_type in disclosure_keys


def _disclosure_from_rule(
    rule: _DisclosureRule, *, required_for: ProposalNarrativeClientAudience
) -> ProposalNarrativeDisclosure:
    return ProposalNarrativeDisclosure(
        disclosure_id=rule.disclosure_id,
        jurisdiction=rule.jurisdiction,
        product_type=rule.product_type,
        required_for=required_for,
        text=rule.text,
        source_authority="lotus-advise.rfc0023.slice6",
        policy_version=NARRATIVE_POLICY_VERSION,
    )


def resolve_proposal_narrative_policy(
    *,
    artifact: ProposalArtifact,
    request: ProposalNarrativeRequest,
) -> ProposalNarrativePolicy:
    jurisdiction = normalize_policy_token(request.jurisdiction)
    product_types = resolve_narrative_product_types(artifact=artifact, request=request)
    risk_posture = resolve_narrative_risk_posture(artifact)
    disclosures = _select_disclosures(
        jurisdiction=jurisdiction,
        product_types=product_types,
        risk_posture=risk_posture,
        required_for=request.client_audience,
    )

    client_ready_blockers: list[str] = []
    if request.client_audience == "CLIENT_READY":
        if jurisdiction not in SUPPORTED_DISCLOSURE_JURISDICTIONS:
            client_ready_blockers.append("CLIENT_READY_DISCLOSURE_POLICY_UNAVAILABLE")
        if not disclosures:
            client_ready_blockers.append("CLIENT_READY_DISCLOSURES_NOT_SELECTED")
        client_ready_blockers.append("CLIENT_READY_NARRATIVE_RELEASE_NOT_SUPPORTED")

    return ProposalNarrativePolicy(
        policy_version=NARRATIVE_POLICY_VERSION,
        status=("BLOCKED_CLIENT_READY" if client_ready_blockers else "READY_FOR_ADVISOR_REVIEW"),
        context=ProposalNarrativePolicyContext(
            jurisdiction=jurisdiction,
            product_types=product_types,
            risk_posture=risk_posture,
            client_audience=request.client_audience,
        ),
        required_disclosures=disclosures,
        client_ready_blockers=client_ready_blockers,
        prohibited_claims=list(PROHIBITED_CLAIM_PATTERNS),
    )


def evaluate_proposal_narrative_guardrails(
    sections: list[ProposalNarrativeSection],
) -> list[ProposalNarrativeGuardrailResult]:
    results = [result for section in sections for result in _section_guardrail_failures(section)]
    if not results:
        return [
            ProposalNarrativeGuardrailResult(
                guardrail_id="GR_UNSUPPORTED_CLAIMS",
                status="PASS",
                message="No unsupported deterministic narrative claims detected.",
            )
        ]
    return results


def _section_guardrail_failures(
    section: ProposalNarrativeSection,
) -> list[ProposalNarrativeGuardrailResult]:
    return [
        *_unsupported_claim_failures(section),
        *_missing_source_ref_failure(section),
    ]


def _unsupported_claim_failures(
    section: ProposalNarrativeSection,
) -> list[ProposalNarrativeGuardrailResult]:
    text = section.text.lower()
    return [
        ProposalNarrativeGuardrailResult(
            guardrail_id=f"GR_UNSUPPORTED_{pattern.upper().replace(' ', '_')}",
            status="FAIL",
            section_key=section.section_key,
            message=f"Unsupported narrative claim detected: {pattern}.",
        )
        for pattern in PROHIBITED_CLAIM_PATTERNS
        if pattern in text
    ]


def _missing_source_ref_failure(
    section: ProposalNarrativeSection,
) -> list[ProposalNarrativeGuardrailResult]:
    if section.source_refs:
        return []
    return [
        ProposalNarrativeGuardrailResult(
            guardrail_id="GR_MISSING_SOURCE_REF",
            status="FAIL",
            section_key=section.section_key,
            message="Narrative section has no grounding source reference.",
        )
    ]
