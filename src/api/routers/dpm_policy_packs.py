import os
from typing import Annotated, Optional

from fastapi import APIRouter, Header, status

from src.core.dpm.policy_packs import (
    DpmEffectivePolicyPackResolution,
    DpmPolicyPackCatalogResponse,
    parse_policy_pack_catalog,
    resolve_effective_policy_pack,
)
from src.core.dpm.tenant_policy_packs import build_tenant_policy_pack_resolver

router = APIRouter(tags=["DPM Run Supportability"])


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def resolve_dpm_policy_pack(
    *,
    request_policy_pack_id: Optional[str],
    tenant_default_policy_pack_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> DpmEffectivePolicyPackResolution:
    resolved_tenant_default_policy_pack_id = tenant_default_policy_pack_id
    if resolved_tenant_default_policy_pack_id is None:
        tenant_policy_pack_resolver = build_tenant_policy_pack_resolver(
            enabled=_env_flag("DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED", False),
            mapping_json=os.getenv("DPM_TENANT_POLICY_PACK_MAP_JSON"),
        )
        resolved_tenant_default_policy_pack_id = tenant_policy_pack_resolver.resolve(
            tenant_id=tenant_id
        )
    return resolve_effective_policy_pack(
        policy_packs_enabled=_env_flag("DPM_POLICY_PACKS_ENABLED", False),
        request_policy_pack_id=request_policy_pack_id,
        tenant_default_policy_pack_id=resolved_tenant_default_policy_pack_id,
        global_default_policy_pack_id=os.getenv("DPM_DEFAULT_POLICY_PACK_ID"),
    )


def load_dpm_policy_pack_catalog():
    return parse_policy_pack_catalog(os.getenv("DPM_POLICY_PACK_CATALOG_JSON"))


@router.get(
    "/rebalance/policies/effective",
    response_model=DpmEffectivePolicyPackResolution,
    status_code=status.HTTP_200_OK,
    summary="Resolve Effective DPM Policy Pack",
    description=(
        "Returns the effective DPM policy-pack resolution using configured precedence "
        "(request, tenant default, global default). This endpoint is read-only and "
        "intended for supportability and integration diagnostics."
    ),
)
def get_effective_dpm_policy_pack(
    request_policy_pack_id: Annotated[
        Optional[str],
        Header(
            alias="X-Policy-Pack-Id",
            description="Optional request-scoped policy-pack identifier.",
            examples=["dpm_standard_v1"],
        ),
    ] = None,
    tenant_default_policy_pack_id: Annotated[
        Optional[str],
        Header(
            alias="X-Tenant-Policy-Pack-Id",
            description="Optional tenant-default policy-pack identifier from upstream context.",
            examples=["dpm_tenant_default_v1"],
        ),
    ] = None,
    tenant_id: Annotated[
        Optional[str],
        Header(
            alias="X-Tenant-Id",
            description="Optional tenant identifier used for tenant policy-pack default lookup.",
            examples=["tenant_001"],
        ),
    ] = None,
) -> DpmEffectivePolicyPackResolution:
    return resolve_dpm_policy_pack(
        request_policy_pack_id=request_policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
    )


@router.get(
    "/rebalance/policies/catalog",
    response_model=DpmPolicyPackCatalogResponse,
    status_code=status.HTTP_200_OK,
    summary="List DPM Policy Pack Catalog",
    description=(
        "Returns the currently configured DPM policy-pack catalog and the effective "
        "selection context for optional request and tenant headers."
    ),
)
def get_dpm_policy_pack_catalog(
    request_policy_pack_id: Annotated[
        Optional[str],
        Header(
            alias="X-Policy-Pack-Id",
            description="Optional request-scoped policy-pack identifier.",
            examples=["dpm_standard_v1"],
        ),
    ] = None,
    tenant_default_policy_pack_id: Annotated[
        Optional[str],
        Header(
            alias="X-Tenant-Policy-Pack-Id",
            description="Optional tenant-default policy-pack identifier from upstream context.",
            examples=["dpm_tenant_default_v1"],
        ),
    ] = None,
    tenant_id: Annotated[
        Optional[str],
        Header(
            alias="X-Tenant-Id",
            description="Optional tenant identifier used for tenant policy-pack default lookup.",
            examples=["tenant_001"],
        ),
    ] = None,
) -> DpmPolicyPackCatalogResponse:
    resolution = resolve_dpm_policy_pack(
        request_policy_pack_id=request_policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
    )
    catalog = load_dpm_policy_pack_catalog()
    items = sorted(catalog.values(), key=lambda item: item.policy_pack_id)
    selected_policy_pack_id = resolution.selected_policy_pack_id
    return DpmPolicyPackCatalogResponse(
        enabled=resolution.enabled,
        total=len(items),
        selected_policy_pack_id=selected_policy_pack_id,
        selected_policy_pack_present=(
            selected_policy_pack_id is not None and selected_policy_pack_id in catalog
        ),
        selected_policy_pack_source=resolution.source,
        items=items,
    )
