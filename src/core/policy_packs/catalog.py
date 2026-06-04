from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from src.core.policy_packs.catalog_commands import (
    activate_policy_pack_catalog_definition,
    validate_policy_pack_catalog_definition,
)
from src.core.policy_packs.catalog_definitions import (
    catalog_posture,
    definition_key,
    prepare_definition,
    summary_from_definition,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackActivationResponse,
    PolicyPackAuditEvent,
    PolicyPackDetailResponse,
    PolicyPackListResponse,
    PolicyPackValidationResponse,
)
from src.core.policy_packs.catalog_projection import build_policy_pack_detail_response
from src.core.policy_packs.catalog_reference_packs import reference_policy_packs
from src.core.proposals.exceptions import ProposalNotFoundError
from src.core.proposals.idempotency_validation import require_proposal_idempotency_key


def list_policy_pack_versions() -> PolicyPackListResponse:
    return _STORE.list_policy_pack_versions()


def get_policy_pack_version(
    *, policy_pack_id: str, policy_version: str
) -> PolicyPackDetailResponse:
    return _STORE.get_policy_pack_version(
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
    )


def validate_policy_pack_version(
    *,
    policy_pack_id: str,
    policy_version: str,
    requested_by: str,
    idempotency_key: str,
    reason: dict[str, Any],
) -> PolicyPackValidationResponse:
    idempotency_key = require_proposal_idempotency_key(idempotency_key)
    return _STORE.validate_policy_pack_version(
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
        requested_by=requested_by,
        idempotency_key=idempotency_key,
        reason=reason,
    )


def activate_policy_pack_version(
    *,
    policy_pack_id: str,
    policy_version: str,
    activated_by: str,
    source_content_hash: str,
    idempotency_key: str,
    reason: dict[str, Any],
) -> PolicyPackActivationResponse:
    idempotency_key = require_proposal_idempotency_key(idempotency_key)
    return _STORE.activate_policy_pack_version(
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
        activated_by=activated_by,
        source_content_hash=source_content_hash,
        idempotency_key=idempotency_key,
        reason=reason,
    )


def reset_policy_pack_catalog_for_tests() -> None:
    _STORE.reset()


class PolicyPackCatalogStore:
    def __init__(self, definitions: list[dict[str, Any]]) -> None:
        self._source_definitions = deepcopy(definitions)
        self.reset()

    def reset(self) -> None:
        self._definitions = {
            definition_key(definition): prepare_definition(definition)
            for definition in deepcopy(self._source_definitions)
        }
        self._events: dict[tuple[str, str], list[PolicyPackAuditEvent]] = {
            key: [] for key in self._definitions
        }
        self._idempotency: dict[str, tuple[str, PolicyPackAuditEvent]] = {}

    def list_policy_pack_versions(self) -> PolicyPackListResponse:
        return PolicyPackListResponse(
            items=[
                summary_from_definition(definition)
                for definition in sorted(
                    self._definitions.values(),
                    key=lambda item: (item["policy_pack_id"], item["policy_version"]),
                )
            ],
            catalog_posture=catalog_posture(),
        )

    def get_policy_pack_version(
        self, *, policy_pack_id: str, policy_version: str
    ) -> PolicyPackDetailResponse:
        definition = self._load_definition(
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
        )
        return self._detail_from_definition(definition)

    def validate_policy_pack_version(
        self,
        *,
        policy_pack_id: str,
        policy_version: str,
        requested_by: str,
        idempotency_key: str,
        reason: dict[str, Any],
    ) -> PolicyPackValidationResponse:
        definition = self._load_definition(
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
        )
        return validate_policy_pack_catalog_definition(
            definition=definition,
            events=self._events,
            idempotency=self._idempotency,
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
            requested_by=requested_by,
            idempotency_key=idempotency_key,
            reason=reason,
        )

    def activate_policy_pack_version(
        self,
        *,
        policy_pack_id: str,
        policy_version: str,
        activated_by: str,
        source_content_hash: str,
        idempotency_key: str,
        reason: dict[str, Any],
    ) -> PolicyPackActivationResponse:
        definition = self._load_definition(
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
        )
        return activate_policy_pack_catalog_definition(
            definition=definition,
            events=self._events,
            idempotency=self._idempotency,
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
            activated_by=activated_by,
            source_content_hash=source_content_hash,
            idempotency_key=idempotency_key,
            reason=reason,
        )

    def _load_definition(self, *, policy_pack_id: str, policy_version: str) -> dict[str, Any]:
        definition = self._definitions.get((policy_pack_id, policy_version))
        if definition is None:
            raise ProposalNotFoundError("POLICY_PACK_VERSION_NOT_FOUND")
        return cast(dict[str, Any], definition)

    def _detail_from_definition(self, definition: dict[str, Any]) -> PolicyPackDetailResponse:
        return build_policy_pack_detail_response(definition=definition, events=self._events)


_STORE = PolicyPackCatalogStore(reference_policy_packs())
