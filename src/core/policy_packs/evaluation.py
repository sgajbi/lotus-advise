from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from src.core.policy_packs.catalog import get_policy_pack_version
from src.core.policy_packs.evaluation_applicability import evaluate_policy_pack_applicability
from src.core.policy_packs.evaluation_models import (
    PolicyPackEvaluationResponse,
    PolicyRuleEvaluationResult,
)
from src.core.policy_packs.evaluation_rules import evaluate_policy_rule
from src.core.policy_packs.supportability import (
    POLICY_EVALUATION_ENGINE_CONTRACT_VERSION,
    policy_runtime_supportability,
)
from src.core.proposals.exceptions import ProposalValidationError
from src.core.proposals.policy_source_readiness import build_policy_source_readiness
from src.core.proposals.source_readiness_common import dict_at, overall_posture

_EVALUATION_CONTRACT_VERSION = POLICY_EVALUATION_ENGINE_CONTRACT_VERSION


def evaluate_policy_pack_version(
    *,
    evidence_bundle: dict[str, Any],
    policy_pack_id: str,
    policy_version: str,
) -> PolicyPackEvaluationResponse:
    """Evaluate an active policy pack against source-backed proposal evidence.

    This is the RFC-0025 Slice 6 engine behind the certified Advise policy APIs. It does not
    create durable policy evaluation records directly. Certified Advise APIs own persistence,
    review queue, lineage, replay, sign-off source-package access, report package handoff, and
    Gateway/Workbench consumption; client-ready publication remains blocked.
    """

    detail = get_policy_pack_version(
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
    )
    _require_active_policy_version(activation_state=detail.policy_pack.activation_state)
    return _evaluate_policy_pack_detail(evidence_bundle=evidence_bundle, detail=detail)


def evaluate_policy_pack_version_for_replay(
    *,
    evidence_bundle: dict[str, Any],
    policy_pack_id: str,
    policy_version: str,
) -> PolicyPackEvaluationResponse:
    detail = get_policy_pack_version(
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
    )
    if detail.policy_pack.activation_state not in {"ACTIVE", "SUPERSEDED", "DISABLED"}:
        raise ProposalValidationError("POLICY_PACK_VERSION_NOT_REPLAY_ELIGIBLE")
    return _evaluate_policy_pack_detail(evidence_bundle=evidence_bundle, detail=detail)


def _evaluate_policy_pack_detail(
    *,
    evidence_bundle: dict[str, Any],
    detail: Any,
) -> PolicyPackEvaluationResponse:

    source_posture = _source_posture(evidence_bundle)
    applicability = evaluate_policy_pack_applicability(
        evidence_bundle=evidence_bundle,
        applicability=detail.applicability,
    )
    if applicability.status != "APPLICABLE":
        return PolicyPackEvaluationResponse(
            contract_version=_EVALUATION_CONTRACT_VERSION,
            policy_pack=detail.policy_pack,
            evaluation_status="NOT_APPLICABLE"
            if applicability.status == "NOT_APPLICABLE"
            else "BLOCKED",
            applicability=applicability,
            source_posture=source_posture,
            rule_results=[],
            supportability=_supportability(),
        )

    results = [
        evaluate_policy_rule(
            rule=rule,
            evidence_bundle=evidence_bundle,
            source_posture=source_posture,
            jurisdiction=applicability.matched_selectors.get("jurisdiction", ""),
            client_segment=applicability.matched_selectors.get("client_segment", ""),
        )
        for rule in detail.rules
    ]
    return PolicyPackEvaluationResponse(
        contract_version=_EVALUATION_CONTRACT_VERSION,
        policy_pack=detail.policy_pack,
        evaluation_status=_aggregate_status(results),
        applicability=applicability,
        source_posture=source_posture,
        rule_results=results,
        supportability=_supportability(),
    )


def _require_active_policy_version(*, activation_state: str) -> None:
    if activation_state != "ACTIVE":
        raise ProposalValidationError("POLICY_PACK_VERSION_NOT_ACTIVE_FOR_EVALUATION")


def _source_posture(evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    posture = dict_at(evidence_bundle, "policy_source_readiness")
    if posture:
        return cast(dict[str, Any], deepcopy(posture))
    return cast(dict[str, Any], build_policy_source_readiness(evidence_bundle))


def _aggregate_status(results: list[PolicyRuleEvaluationResult]) -> str:
    return cast(str, overall_posture([{"status": result.status} for result in results]))


def _supportability() -> dict[str, Any]:
    return dict(policy_runtime_supportability())
