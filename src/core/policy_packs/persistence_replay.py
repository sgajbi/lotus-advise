from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.common.canonical import hash_canonical_payload
from src.core.policy_packs.catalog import get_policy_pack_version
from src.core.policy_packs.evaluation import evaluate_policy_pack_version_for_replay
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationRecord,
    PolicyEvaluationReplayResponse,
)
from src.core.policy_packs.persistence_record_builder import policy_evaluation_hash
from src.core.policy_packs.supportability import POLICY_EVALUATION_PERSISTENCE_CONTRACT_VERSION
from src.core.proposals.exceptions import ProposalNotFoundError


def build_policy_evaluation_replay_response(
    *,
    record: PolicyEvaluationRecord,
    evidence_bundle: dict[str, Any] | None,
) -> PolicyEvaluationReplayResponse:
    detail = _policy_pack_detail_for_replay(record=record)
    comparison: dict[str, Any] = {
        "stored_policy_version": record.policy_version,
        "current_policy_version": detail.policy_pack.policy_version if detail is not None else None,
        "policy_version_matches": detail is not None
        and detail.policy_pack.policy_version == record.policy_version,
        "stored_policy_content_hash": record.policy_content_hash,
        "current_policy_content_hash": detail.policy_pack.content_hash
        if detail is not None
        else None,
        "policy_content_hash_matches": detail is not None
        and detail.policy_pack.content_hash == record.policy_content_hash,
        "policy_activation_state": detail.policy_pack.activation_state
        if detail is not None
        else "UNAVAILABLE",
        "stored_source_evidence_hash": record.source_evidence_hash,
        "replayed_source_evidence_hash": record.source_evidence_hash,
        "source_evidence_hash_matches": True,
        "stored_evaluation_hash": record.evaluation_hash,
        "replayed_evaluation_hash": record.evaluation_hash,
        "evaluation_hash_matches": True,
        "replay_reason_code": "POLICY_REPLAY_STORED_ONLY",
    }
    if evidence_bundle is not None:
        replayed_source_hash = hash_canonical_payload(evidence_bundle)
        replayed_hash = None
        reason_code = _replay_reason_code(comparison=comparison)
        if reason_code == "POLICY_REPLAY_ELIGIBLE":
            replayed_evaluation = evaluate_policy_pack_version_for_replay(
                evidence_bundle=deepcopy(evidence_bundle),
                policy_pack_id=record.policy_pack_id,
                policy_version=record.policy_version,
            )
            replayed_hash = policy_evaluation_hash(
                evaluation=_evaluation_payload_for_hash(
                    record=record,
                    replayed_evaluation=replayed_evaluation,
                ),
                source_evidence_hash=replayed_source_hash,
                policy_content_hash=record.policy_content_hash,
            )
            reason_code = (
                "POLICY_REPLAY_EXACT_MATCH"
                if (
                    replayed_source_hash == record.source_evidence_hash
                    and replayed_hash == record.evaluation_hash
                )
                else "POLICY_REPLAY_HASH_DRIFT"
            )
        comparison.update(
            {
                "replayed_source_evidence_hash": replayed_source_hash,
                "source_evidence_hash_matches": replayed_source_hash == record.source_evidence_hash,
                "replayed_evaluation_hash": replayed_hash,
                "evaluation_hash_matches": replayed_hash == record.evaluation_hash,
                "replay_reason_code": reason_code,
            }
        )
    return PolicyEvaluationReplayResponse(
        evaluation_id=record.evaluation_id,
        replay_contract_version=POLICY_EVALUATION_PERSISTENCE_CONTRACT_VERSION,
        policy_pack_id=record.policy_pack_id,
        policy_version=record.policy_version,
        source_refs=list(record.source_refs),
        source_gaps=list(record.source_gaps),
        hash_comparison=comparison,
        replay_metadata=deepcopy(record.replay_metadata_json),
    )


def _policy_pack_detail_for_replay(*, record: PolicyEvaluationRecord) -> Any | None:
    try:
        return get_policy_pack_version(
            policy_pack_id=record.policy_pack_id,
            policy_version=record.policy_version,
        )
    except ProposalNotFoundError:
        return None


def _evaluation_payload_for_hash(
    *, record: PolicyEvaluationRecord, replayed_evaluation: Any
) -> Any:
    original_policy_pack = record.evaluation_json.get("policy_pack", {})
    original_activation_state = original_policy_pack.get("activation_state")
    if not isinstance(original_activation_state, str):
        return replayed_evaluation
    return replayed_evaluation.model_copy(
        update={
            "policy_pack": replayed_evaluation.policy_pack.model_copy(
                update={"activation_state": original_activation_state}
            )
        }
    )


def _replay_reason_code(*, comparison: dict[str, Any]) -> str:
    if comparison["current_policy_version"] is None:
        return "POLICY_DEFINITION_UNAVAILABLE_FOR_REPLAY"
    if not comparison["policy_content_hash_matches"]:
        return "POLICY_CONTENT_HASH_DRIFT_REPLAY_BLOCKED"
    if comparison["policy_activation_state"] not in {"ACTIVE", "SUPERSEDED", "DISABLED"}:
        return "POLICY_VERSION_NOT_REPLAY_ELIGIBLE"
    return "POLICY_REPLAY_ELIGIBLE"
