from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core.proposals.memo_models import ProposalMemoMaterialClaim, ProposalMemoSectionStatus


@dataclass(frozen=True)
class MemoSectionEnrichment:
    summary: str
    claims: list[ProposalMemoMaterialClaim] = field(default_factory=list)
    forced_status: ProposalMemoSectionStatus | None = None
    forced_missing: list[str] = field(default_factory=list)
    forced_reasons: list[str] = field(default_factory=list)


def build_suitability_best_interest_enrichment(
    *, artifact: dict[str, Any], evidence_bundle: dict[str, Any]
) -> MemoSectionEnrichment:
    suitability = _dict_at(artifact, "suitability_summary")
    product_evidence = _product_evidence(evidence_bundle)
    missing = list(product_evidence["missing"])
    reasons = list(product_evidence["reason_codes"])
    claims: list[ProposalMemoMaterialClaim] = []
    summary = _suitability_summary(suitability=suitability, product_evidence=product_evidence)

    if suitability.get("status") == "AVAILABLE":
        claims.append(
            _claim(
                claim_id="suitability_and_best_interest.claim.1",
                text=(
                    f"Suitability evidence records {suitability.get('new_issues', 0)} new, "
                    f"{suitability.get('persistent_issues', 0)} persistent, and "
                    f"{suitability.get('resolved_issues', 0)} resolved issue(s)."
                ),
                evidence_refs=[
                    "artifact.suitability_summary",
                    "artifact.proposal_decision_summary.suitability_posture",
                ],
                source_refs=["lotus-advise:proposal_decision_summary"],
                reason_codes=["SUITABILITY_POSTURE_CAPTURED"],
            )
        )
    else:
        missing.append("suitability_summary")
        reasons.append("SUITABILITY_EVIDENCE_NOT_AVAILABLE")

    if product_evidence["covered_instruments"]:
        claims.append(
            _claim(
                claim_id="suitability_and_best_interest.claim.2",
                text=(
                    "Product eligibility and complexity evidence is present for proposed "
                    f"instrument(s): {', '.join(product_evidence['covered_instruments'])}."
                ),
                evidence_refs=["evidence_bundle.inputs.shelf_entries"],
                source_refs=["lotus-core:product_eligibility_complexity"],
                reason_codes=["PRODUCT_ELIGIBILITY_COMPLEXITY_CAPTURED"],
            )
        )

    return MemoSectionEnrichment(
        summary=summary,
        claims=claims,
        forced_missing=_unique(missing),
        forced_reasons=_unique(reasons),
    )


def build_fee_cost_tax_friction_enrichment(*, artifact: dict[str, Any]) -> MemoSectionEnrichment:
    assumptions = _dict_at(artifact, "assumptions_and_limits")
    costs = _dict_at(assumptions, "costs_and_fees")
    tax = _dict_at(assumptions, "tax")
    execution = _dict_at(assumptions, "execution")
    missing = []
    reasons = []
    if not costs.get("included"):
        missing.append("fee_evidence")
        missing.append("cost_evidence")
        reasons.append("MEMO_COST_FEE_EVIDENCE_NOT_MODELED")
    if not tax.get("included"):
        missing.append("tax_evidence")
        reasons.append("MEMO_TAX_EVIDENCE_NOT_MODELED")
    if not execution.get("included"):
        missing.append("execution_friction_evidence")
        reasons.append("MEMO_EXECUTION_FRICTION_NOT_MODELED")

    notes = [
        _note("Costs and fees", costs),
        _note("Tax", tax),
        _note("Execution friction", execution),
    ]
    claims = [
        _claim(
            claim_id="fees_costs_tax_and_frictions.claim.1",
            text=" ".join(notes),
            evidence_refs=["artifact.assumptions_and_limits"],
            source_refs=["lotus-advise:proposal_artifact_assumptions"],
            reason_codes=["COST_TAX_FRICTION_LIMITATIONS_CAPTURED"],
        )
    ]
    return MemoSectionEnrichment(
        summary=" ".join(notes),
        claims=claims,
        forced_status="PENDING_REVIEW" if missing else None,
        forced_missing=_unique(missing),
        forced_reasons=_unique(reasons),
    )


def build_conflict_disclosure_enrichment(
    *, artifact: dict[str, Any], evidence_bundle: dict[str, Any]
) -> MemoSectionEnrichment:
    disclosures = _dict_at(artifact, "disclosures")
    product_docs = _list_at(disclosures, "product_docs")
    proposed_instruments = _proposed_instruments(evidence_bundle)
    documented_instruments = {
        str(item.get("instrument_id"))
        for item in product_docs
        if isinstance(item, dict) and item.get("instrument_id")
    }
    missing_docs = sorted(set(proposed_instruments) - documented_instruments)
    missing = ["conflict_evidence"]
    reasons = ["MEMO_CONFLICT_POLICY_PACK_NOT_IMPLEMENTED"]
    if missing_docs:
        missing.append("product_document_evidence")
        reasons.append("PRODUCT_DOCUMENTATION_INCOMPLETE_FOR_PROPOSED_TRADES")

    risk_disclaimer = str(disclosures.get("risk_disclaimer") or "").strip()
    claims = []
    if risk_disclaimer:
        claims.append(
            _claim(
                claim_id="conflicts_and_disclosures.claim.1",
                text=f"Risk disclosure captured: {risk_disclaimer}",
                evidence_refs=["artifact.disclosures.risk_disclaimer"],
                source_refs=["lotus-advise:proposal_artifact_disclosures"],
                reason_codes=["RISK_DISCLOSURE_CAPTURED"],
            )
        )
    if documented_instruments:
        claims.append(
            _claim(
                claim_id="conflicts_and_disclosures.claim.2",
                text=(
                    "Product-document references are available for proposed instrument(s): "
                    f"{', '.join(sorted(documented_instruments))}."
                ),
                evidence_refs=["artifact.disclosures.product_docs"],
                source_refs=["lotus-advise:proposal_artifact_disclosures"],
                reason_codes=["PRODUCT_DOCUMENT_REFERENCES_CAPTURED"],
            )
        )

    summary = (
        "Disclosure evidence is captured from the proposal artifact; conflict-of-interest "
        "evidence remains review-required until policy packs are implemented."
    )
    return MemoSectionEnrichment(
        summary=summary,
        claims=claims,
        forced_status="PENDING_REVIEW",
        forced_missing=_unique(missing),
        forced_reasons=_unique(reasons),
    )


def _product_evidence(evidence_bundle: dict[str, Any]) -> dict[str, list[str]]:
    proposed = _proposed_instruments(evidence_bundle)
    shelf_by_instrument = {
        str(row.get("instrument_id")): row
        for row in _list_at(_dict_at(evidence_bundle, "inputs"), "shelf_entries")
        if isinstance(row, dict) and row.get("instrument_id")
    }
    covered: list[str] = []
    missing: list[str] = []
    reasons: list[str] = []
    for instrument_id in proposed:
        row = shelf_by_instrument.get(instrument_id)
        if row is None:
            missing.append(f"shelf_entry:{instrument_id}")
            reasons.append("PRODUCT_SHELF_ENTRY_MISSING_FOR_PROPOSED_TRADE")
            continue
        if _has_eligibility_and_complexity(row):
            covered.append(instrument_id)
            continue
        missing.append(f"product_eligibility_complexity:{instrument_id}")
        reasons.append("PRODUCT_ELIGIBILITY_COMPLEXITY_MISSING_FOR_PROPOSED_TRADE")
    return {
        "covered_instruments": covered,
        "missing": missing,
        "reason_codes": reasons,
    }


def _suitability_summary(
    *, suitability: dict[str, Any], product_evidence: dict[str, list[str]]
) -> str:
    if suitability.get("status") != "AVAILABLE":
        return (
            "Suitability and best-interest posture requires review because suitability evidence "
            "is unavailable."
        )
    return (
        f"Suitability has {suitability.get('new_issues', 0)} new issue(s), "
        f"{suitability.get('persistent_issues', 0)} persistent issue(s), and "
        f"{suitability.get('resolved_issues', 0)} resolved issue(s). "
        f"Product eligibility coverage: {len(product_evidence['covered_instruments'])} "
        "proposed instrument(s)."
    )


def _proposed_instruments(evidence_bundle: dict[str, Any]) -> list[str]:
    trades = _list_at(_dict_at(evidence_bundle, "inputs"), "proposed_trades")
    return _unique(
        [
            str(row.get("instrument_id"))
            for row in trades
            if isinstance(row, dict) and row.get("instrument_id")
        ]
    )


def _has_eligibility_and_complexity(row: dict[str, Any]) -> bool:
    raw_attributes = row.get("attributes")
    attributes: dict[str, Any] = raw_attributes if isinstance(raw_attributes, dict) else {}
    return bool(row.get("eligibility") or attributes.get("eligibility")) and bool(
        row.get("complexity")
        or row.get("product_complexity")
        or attributes.get("complexity")
        or attributes.get("product_complexity")
    )


def _note(label: str, payload: dict[str, Any]) -> str:
    note = str(payload.get("notes") or "No note provided.").strip()
    included = "included" if payload.get("included") else "not included"
    return f"{label} are {included}: {note}"


def _claim(
    *,
    claim_id: str,
    text: str,
    evidence_refs: list[str],
    source_refs: list[str],
    reason_codes: list[str],
) -> ProposalMemoMaterialClaim:
    return ProposalMemoMaterialClaim(
        claim_id=claim_id,
        text=text,
        evidence_refs=evidence_refs,
        source_authority_refs=source_refs,
        reason_codes=reason_codes,
    )


def _dict_at(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _list_at(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
