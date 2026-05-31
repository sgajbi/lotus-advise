from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, TypeVar, cast

from src.core.advisor_cockpit.action_sources import CockpitActionSourceRefs
from src.core.advisor_cockpit.models import (
    AdvisorCockpitOwnerRole,
    AdvisorCockpitSlaAgeBand,
    CockpitDependencyReadiness,
    CockpitEvidenceRef,
    CockpitLineageRef,
    CockpitSourceReadinessGap,
)
from src.core.advisor_cockpit.projection_bounds import (
    bounded_content_hash,
    bounded_optional_reference,
    bounded_reference,
    bounded_summary,
)

LOTUS_ADVISE_SOURCE_SYSTEM = "lotus-advise"
T = TypeVar("T")


def build_action_item_id(action_family: str, source_action_id: str) -> str:
    return cast(
        str,
        bounded_reference(
            f"aci_{normalize_action_identifier(action_family)}_"
            f"{normalize_action_identifier(source_action_id)}"
        ),
    )


def normalize_action_identifier(value: str) -> str:
    normalized = "".join(character.lower() if character.isalnum() else "_" for character in value)
    return "_".join(part for part in normalized.split("_") if part)


def evidence_ref(
    *,
    evidence_id: str,
    evidence_type: str,
    summary: str,
    access_class: Literal[
        "CUSTOMER_CONSUMABLE_SUMMARY",
        "RESTRICTED_CUSTOMER_EVIDENCE",
        "OPERATOR_ONLY_SUPPORTABILITY",
        "INTERNAL_ONLY_DIAGNOSTICS",
    ],
) -> CockpitEvidenceRef:
    return CockpitEvidenceRef(
        evidence_id=bounded_reference(evidence_id),
        evidence_type=bounded_reference(evidence_type),
        source_system=LOTUS_ADVISE_SOURCE_SYSTEM,
        access_class=access_class,
        summary=bounded_summary(summary),
    )


def lineage_refs(lineage_id: str | None, content_hash: str | None) -> list[CockpitLineageRef]:
    if lineage_id is None:
        return []
    return [
        CockpitLineageRef(
            lineage_id=bounded_reference(lineage_id),
            source_system=LOTUS_ADVISE_SOURCE_SYSTEM,
            content_hash=bounded_content_hash(content_hash),
        )
    ]


def source_readiness_gap(
    *,
    source_family: str,
    gap_code: str,
    owner_role: AdvisorCockpitOwnerRole,
    message: str,
) -> CockpitSourceReadinessGap:
    return CockpitSourceReadinessGap(
        source_family=bounded_reference(source_family),
        gap_code=bounded_reference(gap_code),
        owner_role=owner_role,
        message=bounded_summary(message),
    )


def dependency_readiness(
    *,
    dependency: str,
    state: Literal["READY", "DEGRADED", "UNAVAILABLE", "NOT_CONFIGURED", "UNSUPPORTED"],
    reason_code: str,
    summary: str,
) -> CockpitDependencyReadiness:
    return CockpitDependencyReadiness(
        dependency=bounded_reference(dependency),
        state=state,
        reason_code=bounded_reference(reason_code),
        summary=bounded_summary(summary),
    )


def initial_sla_age_band(due_at: str | None) -> AdvisorCockpitSlaAgeBand:
    return "DUE_SOON" if due_at else "NOT_APPLICABLE"


def bounded_source_refs(source_refs: CockpitActionSourceRefs) -> CockpitActionSourceRefs:
    return CockpitActionSourceRefs(
        client_ref=bounded_optional_reference(source_refs.client_ref),
        household_ref=bounded_optional_reference(source_refs.household_ref),
        portfolio_id=bounded_optional_reference(source_refs.portfolio_id),
        proposal_id=bounded_optional_reference(source_refs.proposal_id),
        workspace_id=bounded_optional_reference(source_refs.workspace_id),
        memo_id=bounded_optional_reference(source_refs.memo_id),
        policy_evaluation_id=bounded_optional_reference(source_refs.policy_evaluation_id),
        report_ref=bounded_optional_reference(source_refs.report_ref),
        execution_ref=bounded_optional_reference(source_refs.execution_ref),
    )


def unique_ordered(values: Sequence[T]) -> list[T]:
    unique: list[T] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique
