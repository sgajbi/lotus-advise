from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from src.core.common.canonical import hash_canonical_payload
from src.core.policy_packs.catalog_definitions import (
    CATALOG_CONTRACT_VERSION,
    REFERENCE_POSTURE,
    catalog_posture,
    definition_key,
    prepare_definition,
    summary_from_definition,
    validate_definition,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackActivationResponse,
    PolicyPackAuditEvent,
    PolicyPackDetailResponse,
    PolicyPackListResponse,
    PolicyPackValidationResponse,
)
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
)
from src.core.proposals.idempotency_validation import require_proposal_idempotency_key

_CATALOG_CONTRACT_VERSION = CATALOG_CONTRACT_VERSION
_REFERENCE_POSTURE = REFERENCE_POSTURE


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
        request_hash = hash_canonical_payload(
            {
                "operation": "POLICY_PACK_VALIDATED",
                "policy_pack_id": policy_pack_id,
                "policy_version": policy_version,
                "requested_by": requested_by,
                "content_hash": definition["content_hash"],
                "reason": reason,
            }
        )
        replayed = self._find_replayed_event(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replayed is not None:
            return PolicyPackValidationResponse(
                policy_pack=summary_from_definition(definition),
                validation_status="READY",
                diagnostics=list(replayed.reason.get("diagnostics", [])),
                validation_event=replayed,
                replayed=True,
            )

        diagnostics = validate_definition(definition)
        if diagnostics:
            raise ProposalValidationError(";".join(diagnostics))
        event = self._append_event(
            event_type="POLICY_PACK_VALIDATED",
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
            actor_id=requested_by,
            content_hash=str(definition["content_hash"]),
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            reason={
                "validation_status": "READY",
                "diagnostics": [],
                "dry_run_status": "REFERENCE_FIXTURES_VALIDATED",
                "sample_fixture_refs": list(definition["sample_fixture_refs"]),
                "reason": deepcopy(reason),
                "reference_posture": _REFERENCE_POSTURE,
            },
        )
        return PolicyPackValidationResponse(
            policy_pack=summary_from_definition(definition),
            validation_status="READY",
            diagnostics=[],
            validation_event=event,
            replayed=False,
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
        request_hash = hash_canonical_payload(
            {
                "operation": "POLICY_PACK_ACTIVATED",
                "policy_pack_id": policy_pack_id,
                "policy_version": policy_version,
                "activated_by": activated_by,
                "source_content_hash": source_content_hash,
                "reason": reason,
            }
        )
        replayed = self._find_replayed_event(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replayed is not None:
            return PolicyPackActivationResponse(
                policy_pack=summary_from_definition(definition),
                activation_event=replayed,
                replayed=True,
            )

        if source_content_hash != definition["content_hash"]:
            raise ProposalValidationError("POLICY_PACK_CONTENT_HASH_MISMATCH")
        if definition["activation_state"] == "ACTIVE":
            raise ProposalValidationError("POLICY_PACK_VERSION_ALREADY_ACTIVE_IMMUTABLE")
        diagnostics = validate_definition(definition)
        if diagnostics:
            raise ProposalValidationError(";".join(diagnostics))
        validation_event = self._latest_validation_event(
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
        )
        if validation_event is None:
            raise ProposalValidationError("POLICY_PACK_VALIDATION_REQUIRED_BEFORE_ACTIVATION")
        if definition["maker_checker_required"] and validation_event.actor_id == activated_by:
            raise ProposalValidationError("POLICY_PACK_MAKER_CHECKER_REQUIRES_DIFFERENT_ACTOR")

        definition["activation_state"] = "ACTIVE"
        event = self._append_event(
            event_type="POLICY_PACK_ACTIVATED",
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
            actor_id=activated_by,
            content_hash=str(definition["content_hash"]),
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            reason={
                "activation_state": "ACTIVE",
                "maker_checker_required": definition["maker_checker_required"],
                "validated_by": validation_event.actor_id,
                "validation_event_id": validation_event.event_id,
                "reason": deepcopy(reason),
                "reference_posture": _REFERENCE_POSTURE,
            },
        )
        return PolicyPackActivationResponse(
            policy_pack=summary_from_definition(definition),
            activation_event=event,
            replayed=False,
        )

    def _load_definition(self, *, policy_pack_id: str, policy_version: str) -> dict[str, Any]:
        definition = self._definitions.get((policy_pack_id, policy_version))
        if definition is None:
            raise ProposalNotFoundError("POLICY_PACK_VERSION_NOT_FOUND")
        return definition

    def _detail_from_definition(self, definition: dict[str, Any]) -> PolicyPackDetailResponse:
        key = definition_key(definition)
        return PolicyPackDetailResponse(
            policy_pack=summary_from_definition(definition),
            applicability=deepcopy(definition["applicability"]),
            source_requirements=list(definition["source_requirements"]),
            rules=deepcopy(definition["rules"]),
            disclosure_templates=deepcopy(definition["disclosure_templates"]),
            consent_templates=deepcopy(definition["consent_templates"]),
            approval_routes=deepcopy(definition["approval_routes"]),
            sample_fixture_refs=list(definition["sample_fixture_refs"]),
            supportability={
                **catalog_posture(),
                "activation_lifecycle": "SUPPORTED_BY_RFC0025_SLICE5",
            },
            audit_events=list(self._events[key]),
        )

    def _append_event(
        self,
        *,
        event_type: str,
        policy_pack_id: str,
        policy_version: str,
        actor_id: str,
        content_hash: str,
        idempotency_key: str,
        request_hash: str,
        reason: dict[str, Any],
    ) -> PolicyPackAuditEvent:
        key = (policy_pack_id, policy_version)
        event = PolicyPackAuditEvent(
            event_id=f"ppev_{len(self._events[key]) + 1:06d}",
            event_type=event_type,
            policy_pack_id=policy_pack_id,
            policy_version=policy_version,
            actor_id=actor_id,
            occurred_at=datetime.now(UTC).isoformat(),
            content_hash=content_hash,
            idempotency_key=idempotency_key,
            reason={
                **reason,
                "idempotency_request_hash": request_hash,
                "catalog_contract_version": _CATALOG_CONTRACT_VERSION,
            },
        )
        self._events[key].append(event)
        self._idempotency[idempotency_key] = (request_hash, event)
        return event

    def _find_replayed_event(
        self, *, idempotency_key: str, request_hash: str
    ) -> PolicyPackAuditEvent | None:
        stored = self._idempotency.get(idempotency_key)
        if stored is None:
            return None
        stored_hash, event = stored
        if stored_hash != request_hash:
            raise ProposalIdempotencyConflictError("POLICY_PACK_IDEMPOTENCY_KEY_CONFLICT")
        return event

    def _latest_validation_event(
        self, *, policy_pack_id: str, policy_version: str
    ) -> PolicyPackAuditEvent | None:
        for event in reversed(self._events[(policy_pack_id, policy_version)]):
            if event.event_type == "POLICY_PACK_VALIDATED":
                return event
        return None


_REFERENCE_PACKS: list[dict[str, Any]] = [
    {
        "policy_pack_id": "GLOBAL_PRIVATE_BANKING_BASELINE",
        "policy_version": "2026.05",
        "policy_family": "GLOBAL_PRIVATE_BANKING",
        "display_name": "Global Private Banking Baseline",
        "jurisdiction_scope": ["GLOBAL"],
        "booking_center_code_scope": ["GLOBAL"],
        "legal_entity_scope": ["REFERENCE"],
        "client_segment_scope": ["PRIVATE_BANKING"],
        "product_scope": ["MULTI_ASSET"],
        "effective_from": "2026-05-01",
        "effective_to": "3999-12-31",
        "activation_state": "ACTIVE",
        "owner_role": "ADVISORY_POLICY_STEWARD",
        "maker_checker_required": False,
        "schema_version": _CATALOG_CONTRACT_VERSION,
        "applicability": {
            "jurisdiction_scope": ["GLOBAL"],
            "booking_center_code_scope": ["GLOBAL"],
            "legal_entity_scope": ["REFERENCE"],
            "client_segment_scope": ["PRIVATE_BANKING"],
            "product_scope": ["MULTI_ASSET"],
        },
        "source_requirements": [
            "client_classification",
            "mandate_objectives",
            "mandate_restrictions",
            "holdings_cash_market_data",
            "product_eligibility",
            "risk_policy_metrics",
        ],
        "rules": [
            {
                "rule_id": "GLOBAL_SOURCE_READINESS_REQUIRED",
                "severity": "BLOCKING",
                "required_evidence_fields": [
                    "policy_source_readiness.overall_posture",
                    "policy_source_readiness.source_authority",
                ],
                "source_gap_handling": "PENDING_REVIEW_OR_BLOCKED",
                "outcome_mapping": "NO_POSITIVE_POLICY_OUTCOME_WITH_MISSING_SOURCE_EVIDENCE",
            },
            {
                "rule_id": "GLOBAL_MANDATE_RESTRICTIONS_REVIEW",
                "severity": "REVIEW_REQUIRED",
                "required_evidence_fields": [
                    "core_mandate_objectives_restrictions",
                ],
                "source_gap_handling": "PENDING_REVIEW_OR_BLOCKED",
                "outcome_mapping": "MANDATE_RESTRICTIONS_REQUIRE_ADVISOR_REVIEW",
            },
        ],
        "disclosure_templates": [],
        "consent_templates": [],
        "approval_routes": [
            {
                "route_id": "ADVISOR_REVIEW",
                "owner_role": "ADVISOR",
                "review_sla": "P2D",
            }
        ],
        "sample_fixture_refs": [
            "PB_SG_GLOBAL_BAL_001",
            "fixtures/policy-packs/global-private-banking-baseline.json",
        ],
    },
    {
        "policy_pack_id": "SG_PRIVATE_BANKING_REFERENCE",
        "policy_version": "2026.05",
        "policy_family": "SG_PRIVATE_BANKING",
        "display_name": "Singapore Private Banking Reference",
        "jurisdiction_scope": ["SG"],
        "booking_center_code_scope": ["SG"],
        "legal_entity_scope": ["REFERENCE"],
        "client_segment_scope": ["ACCREDITED_INVESTOR", "PRIVATE_BANKING"],
        "product_scope": ["MULTI_ASSET", "STRUCTURED_PRODUCT", "PRIVATE_ASSET"],
        "effective_from": "2026-05-01",
        "effective_to": "3999-12-31",
        "activation_state": "DRAFT",
        "owner_role": "ADVISORY_POLICY_STEWARD",
        "maker_checker_required": True,
        "schema_version": _CATALOG_CONTRACT_VERSION,
        "applicability": {
            "jurisdiction_scope": ["SG"],
            "booking_center_code_scope": ["SG"],
            "legal_entity_scope": ["REFERENCE"],
            "client_segment_scope": ["ACCREDITED_INVESTOR", "PRIVATE_BANKING"],
            "product_scope": ["MULTI_ASSET", "STRUCTURED_PRODUCT", "PRIVATE_ASSET"],
        },
        "source_requirements": [
            "household_id",
            "account_id",
            "mandate_id",
            "client_classification",
            "product_eligibility",
            "target_market",
            "product_complexity",
            "risk_policy_metrics",
        ],
        "rules": [
            {
                "rule_id": "SG_AI_PRODUCT_ELIGIBILITY_REVIEW",
                "severity": "BLOCKING",
                "required_evidence_fields": [
                    "core_product_eligibility_target_market_complexity",
                    "core_client_profile_classification",
                ],
                "source_gap_handling": "BLOCKED",
                "outcome_mapping": "ELIGIBILITY_REVIEW_REQUIRED",
            },
            {
                "rule_id": "SG_COMPLEX_PRODUCT_DISCLOSURE_REVIEW",
                "severity": "REVIEW_REQUIRED",
                "required_evidence_fields": [
                    "private_asset_or_structured_product_flag",
                    "risk_policy_metrics",
                ],
                "source_gap_handling": "PENDING_REVIEW",
                "outcome_mapping": "DISCLOSURE_AND_CONSENT_REVIEW_REQUIRED",
            },
            {
                "rule_id": "SG_BEST_INTEREST_COST_REVIEW",
                "severity": "REVIEW_REQUIRED",
                "required_evidence_fields": [
                    "fee_cost_tax_friction_evidence",
                ],
                "source_gap_handling": "PENDING_REVIEW",
                "outcome_mapping": "BEST_INTEREST_COST_REASONABLENESS_REVIEW_REQUIRED",
            },
            {
                "rule_id": "SG_CONFLICT_REVIEW",
                "severity": "REVIEW_REQUIRED",
                "required_evidence_fields": [
                    "conflict_evidence",
                    "product_document_evidence",
                ],
                "source_gap_handling": "PENDING_REVIEW",
                "outcome_mapping": "CONFLICT_AND_DISCLOSURE_REVIEW_REQUIRED",
            },
        ],
        "disclosure_templates": [
            {
                "template_id": "SG_COMPLEX_PRODUCT_DISCLOSURE",
                "template_version": "2026.05",
                "audience": "INTERNAL_REVIEW",
            }
        ],
        "consent_templates": [
            {
                "template_id": "SG_COMPLEX_PRODUCT_CONSENT",
                "template_version": "2026.05",
                "audience": "INTERNAL_REVIEW",
            }
        ],
        "approval_routes": [
            {
                "route_id": "INVESTMENT_COUNSELLOR_REVIEW",
                "owner_role": "INVESTMENT_COUNSELLOR",
                "review_sla": "P1D",
            },
            {
                "route_id": "SUPERVISORY_REVIEW",
                "owner_role": "SUPERVISOR",
                "review_sla": "P2D",
            },
        ],
        "sample_fixture_refs": [
            "PB_SG_GLOBAL_BAL_001",
            "fixtures/policy-packs/sg-private-banking-reference.json",
        ],
    },
]

_STORE = PolicyPackCatalogStore(_REFERENCE_PACKS)
