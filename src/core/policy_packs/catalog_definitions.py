from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.common.canonical import hash_canonical_payload
from src.core.policy_packs.catalog_definition_validation import validate_catalog_definition
from src.core.policy_packs.catalog_models import PolicyPackSummary
from src.core.policy_packs.supportability import (
    POLICY_CATALOG_CONTRACT_VERSION,
    REFERENCE_POLICY_PACK_POSTURE,
    policy_runtime_supportability,
)

CATALOG_CONTRACT_VERSION = POLICY_CATALOG_CONTRACT_VERSION
REFERENCE_POSTURE = REFERENCE_POLICY_PACK_POSTURE


def definition_key(definition: dict[str, Any]) -> tuple[str, str]:
    return (str(definition["policy_pack_id"]), str(definition["policy_version"]))


def prepare_definition(definition: dict[str, Any]) -> dict[str, Any]:
    prepared = deepcopy(definition)
    prepared["reference_posture"] = REFERENCE_POSTURE
    prepared["content_hash"] = hash_canonical_payload(
        {
            key: value
            for key, value in prepared.items()
            if key not in {"activation_state", "content_hash"}
        }
    )
    return prepared


def summary_from_definition(definition: dict[str, Any]) -> PolicyPackSummary:
    return PolicyPackSummary(
        policy_pack_id=str(definition["policy_pack_id"]),
        policy_version=str(definition["policy_version"]),
        policy_family=str(definition["policy_family"]),
        display_name=str(definition["display_name"]),
        activation_state=definition["activation_state"],
        reference_posture=str(definition["reference_posture"]),
        maker_checker_required=bool(definition["maker_checker_required"]),
        content_hash=str(definition["content_hash"]),
    )


def catalog_posture() -> dict[str, Any]:
    return dict(policy_runtime_supportability())


def validate_definition(definition: dict[str, Any]) -> list[str]:
    return validate_catalog_definition(definition)
