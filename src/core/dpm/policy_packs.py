import json
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.core.models import EngineOptions

DpmPolicyPackSource = Literal["DISABLED", "REQUEST", "TENANT_DEFAULT", "GLOBAL_DEFAULT", "NONE"]


class DpmEffectivePolicyPackResolution(BaseModel):
    enabled: bool = Field(
        description="Whether policy-pack resolution is enabled for DPM request processing.",
        examples=[False],
    )
    selected_policy_pack_id: Optional[str] = Field(
        default=None,
        description="Resolved policy-pack identifier, when one is selected.",
        examples=["dpm_standard_v1"],
    )
    source: DpmPolicyPackSource = Field(
        description="Resolution source selected by precedence policy.",
        examples=["REQUEST"],
    )


class DpmPolicyPackTurnoverPolicy(BaseModel):
    max_turnover_pct: Optional[Decimal] = Field(
        default=None,
        description="Optional turnover cap override to apply on selected policy-pack.",
        examples=["0.15"],
    )


class DpmPolicyPackTaxPolicy(BaseModel):
    enable_tax_awareness: Optional[bool] = Field(
        default=None,
        description="Optional override for tax-aware sell allocation behavior.",
        examples=[True],
    )
    max_realized_capital_gains: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Optional override for realized capital gains budget in base currency.",
        examples=["100"],
    )


class DpmPolicyPackDefinition(BaseModel):
    policy_pack_id: str = Field(
        description="Unique policy-pack identifier.",
        examples=["dpm_standard_v1"],
    )
    version: str = Field(
        description="Policy-pack version.",
        examples=["1"],
    )
    turnover_policy: DpmPolicyPackTurnoverPolicy = Field(
        default_factory=DpmPolicyPackTurnoverPolicy,
        description="Turnover policy overrides for selected policy-pack.",
    )
    tax_policy: DpmPolicyPackTaxPolicy = Field(
        default_factory=DpmPolicyPackTaxPolicy,
        description="Tax policy overrides for selected policy-pack.",
    )


class DpmPolicyPackCatalogResponse(BaseModel):
    enabled: bool = Field(
        description="Whether policy-pack resolution is enabled in this runtime.",
        examples=[True],
    )
    total: int = Field(
        description="Total number of policy-pack definitions currently available in the catalog.",
        examples=[3],
    )
    selected_policy_pack_id: Optional[str] = Field(
        default=None,
        description=(
            "Resolved policy-pack identifier for the provided request context, "
            "when one is selected."
        ),
        examples=["dpm_standard_v1"],
    )
    selected_policy_pack_present: bool = Field(
        description=(
            "Whether the resolved policy-pack identifier exists in the current policy-pack catalog."
        ),
        examples=[True],
    )
    selected_policy_pack_source: DpmPolicyPackSource = Field(
        description="Resolution source selected by precedence policy.",
        examples=["REQUEST"],
    )
    items: list[DpmPolicyPackDefinition] = Field(
        description="Catalog entries keyed by policy-pack identifier.",
        examples=[
            [
                {
                    "policy_pack_id": "dpm_standard_v1",
                    "version": "1",
                    "turnover_policy": {"max_turnover_pct": "0.10"},
                }
            ]
        ],
    )


def resolve_effective_policy_pack(
    *,
    policy_packs_enabled: bool,
    request_policy_pack_id: Optional[str],
    tenant_default_policy_pack_id: Optional[str],
    global_default_policy_pack_id: Optional[str],
) -> DpmEffectivePolicyPackResolution:
    if not policy_packs_enabled:
        return DpmEffectivePolicyPackResolution(
            enabled=False,
            selected_policy_pack_id=None,
            source="DISABLED",
        )

    request_policy_pack_id = _normalize_policy_pack_id(request_policy_pack_id)
    tenant_default_policy_pack_id = _normalize_policy_pack_id(tenant_default_policy_pack_id)
    global_default_policy_pack_id = _normalize_policy_pack_id(global_default_policy_pack_id)

    if request_policy_pack_id is not None:
        return DpmEffectivePolicyPackResolution(
            enabled=True,
            selected_policy_pack_id=request_policy_pack_id,
            source="REQUEST",
        )
    if tenant_default_policy_pack_id is not None:
        return DpmEffectivePolicyPackResolution(
            enabled=True,
            selected_policy_pack_id=tenant_default_policy_pack_id,
            source="TENANT_DEFAULT",
        )
    if global_default_policy_pack_id is not None:
        return DpmEffectivePolicyPackResolution(
            enabled=True,
            selected_policy_pack_id=global_default_policy_pack_id,
            source="GLOBAL_DEFAULT",
        )
    return DpmEffectivePolicyPackResolution(
        enabled=True,
        selected_policy_pack_id=None,
        source="NONE",
    )


def _normalize_policy_pack_id(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def parse_policy_pack_catalog(catalog_json: Optional[str]) -> dict[str, DpmPolicyPackDefinition]:
    normalized_json = (catalog_json or "").strip()
    if not normalized_json:
        return {}
    try:
        raw = json.loads(normalized_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}

    catalog: dict[str, DpmPolicyPackDefinition] = {}
    for policy_pack_id, definition in raw.items():
        if not isinstance(policy_pack_id, str):
            continue
        if not isinstance(definition, dict):
            continue
        normalized_id = policy_pack_id.strip()
        if not normalized_id:
            continue
        payload = {
            "policy_pack_id": normalized_id,
            "version": str(definition.get("version", "1")),
            "turnover_policy": definition.get("turnover_policy") or {},
            "tax_policy": definition.get("tax_policy") or {},
        }
        try:
            parsed = DpmPolicyPackDefinition.model_validate(payload)
        except Exception:
            continue
        catalog[normalized_id] = parsed
    return catalog


def resolve_policy_pack_definition(
    *,
    resolution: DpmEffectivePolicyPackResolution,
    catalog: dict[str, DpmPolicyPackDefinition],
) -> Optional[DpmPolicyPackDefinition]:
    if resolution.selected_policy_pack_id is None:
        return None
    return catalog.get(resolution.selected_policy_pack_id)


def apply_policy_pack_to_engine_options(
    *,
    options: EngineOptions,
    policy_pack: Optional[DpmPolicyPackDefinition],
) -> EngineOptions:
    if policy_pack is None:
        return options
    updates = {}
    if policy_pack.turnover_policy.max_turnover_pct is not None:
        updates["max_turnover_pct"] = policy_pack.turnover_policy.max_turnover_pct
    if policy_pack.tax_policy.enable_tax_awareness is not None:
        updates["enable_tax_awareness"] = policy_pack.tax_policy.enable_tax_awareness
    if policy_pack.tax_policy.max_realized_capital_gains is not None:
        updates["max_realized_capital_gains"] = policy_pack.tax_policy.max_realized_capital_gains
    if not updates:
        return options
    return options.model_copy(update=updates)
