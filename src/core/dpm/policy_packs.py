from typing import Literal, Optional

from pydantic import BaseModel, Field

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
