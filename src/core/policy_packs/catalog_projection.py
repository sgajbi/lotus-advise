from copy import deepcopy
from typing import Any

from src.core.policy_packs.catalog_definitions import (
    catalog_posture,
    definition_key,
    summary_from_definition,
)
from src.core.policy_packs.catalog_models import (
    PolicyPackAuditEvent,
    PolicyPackDetailResponse,
)


def build_policy_pack_detail_response(
    *,
    definition: dict[str, Any],
    events: dict[tuple[str, str], list[PolicyPackAuditEvent]],
) -> PolicyPackDetailResponse:
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
        audit_events=list(events[key]),
    )
