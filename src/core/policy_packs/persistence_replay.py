from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.common.canonical import hash_canonical_payload
from src.core.policy_packs.catalog import get_policy_pack_version
from src.core.policy_packs.evaluation import evaluate_policy_pack_version
from src.core.policy_packs.persistence_models import (
    PolicyEvaluationRecord,
    PolicyEvaluationReplayResponse,
)
from src.core.policy_packs.persistence_record_builder import policy_evaluation_hash
from src.core.policy_packs.supportability import POLICY_EVALUATION_PERSISTENCE_CONTRACT_VERSION


def build_policy_evaluation_replay_response(
    *,
    record: PolicyEvaluationRecord,
    evidence_bundle: dict[str, Any] | None,
) -> PolicyEvaluationReplayResponse:
    detail = get_policy_pack_version(
        policy_pack_id=record.policy_pack_id,
        policy_version=record.policy_version,
    )
    comparison: dict[str, Any] = {
        "stored_policy_version": record.policy_version,
        "current_policy_version": detail.policy_pack.policy_version,
        "policy_version_matches": detail.policy_pack.policy_version == record.policy_version,
        "stored_policy_content_hash": record.policy_content_hash,
        "current_policy_content_hash": detail.policy_pack.content_hash,
        "policy_content_hash_matches": detail.policy_pack.content_hash
        == record.policy_content_hash,
        "stored_source_evidence_hash": record.source_evidence_hash,
        "replayed_source_evidence_hash": record.source_evidence_hash,
        "source_evidence_hash_matches": True,
        "stored_evaluation_hash": record.evaluation_hash,
        "replayed_evaluation_hash": record.evaluation_hash,
        "evaluation_hash_matches": True,
    }
    if evidence_bundle is not None:
        replayed_evaluation = evaluate_policy_pack_version(
            evidence_bundle=deepcopy(evidence_bundle),
            policy_pack_id=record.policy_pack_id,
            policy_version=record.policy_version,
        )
        replayed_source_hash = hash_canonical_payload(evidence_bundle)
        replayed_hash = policy_evaluation_hash(
            evaluation=replayed_evaluation,
            source_evidence_hash=replayed_source_hash,
            policy_content_hash=detail.policy_pack.content_hash,
        )
        comparison.update(
            {
                "replayed_source_evidence_hash": replayed_source_hash,
                "source_evidence_hash_matches": replayed_source_hash
                == record.source_evidence_hash,
                "replayed_evaluation_hash": replayed_hash,
                "evaluation_hash_matches": replayed_hash == record.evaluation_hash,
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
