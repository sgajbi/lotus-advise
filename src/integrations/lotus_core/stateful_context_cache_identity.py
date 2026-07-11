from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

from src.core.workspace.input_models import WorkspaceStatefulInput
from src.integrations.lotus_core.contracts import ADVISORY_SIMULATION_CONTRACT_VERSION

_ABSENT_DIMENSION = "not-requested"
_SOURCE_DEFAULT = "source-default"
_TENANT_UNSCOPED = "tenant-unscoped"


@dataclass(frozen=True)
class LotusCoreCacheIdentity:
    cache_family: str
    query_base_url: str = _ABSENT_DIMENSION
    control_plane_base_url: str = _ABSENT_DIMENSION
    environment: str = _ABSENT_DIMENSION
    tenant_id: str = _TENANT_UNSCOPED
    contract_version: str = ADVISORY_SIMULATION_CONTRACT_VERSION
    portfolio_id: str = _ABSENT_DIMENSION
    as_of: str = _ABSENT_DIMENSION
    reporting_currency: str = _SOURCE_DEFAULT
    household_id: str = _ABSENT_DIMENSION
    mandate_id: str = _ABSENT_DIMENSION
    benchmark_id: str = _ABSENT_DIMENSION
    look_through_mode: str = _ABSENT_DIMENSION
    allocation_dimensions: str = _SOURCE_DEFAULT
    valuation_options: str = "TRUST_SNAPSHOT"
    risk_options: str = _ABSENT_DIMENSION
    taxonomy_scope: str = _ABSENT_DIMENSION
    security_id: str = _ABSENT_DIMENSION
    instrument_id: str = _ABSENT_DIMENSION
    from_currency: str = _ABSENT_DIMENSION
    to_currency: str = _ABSENT_DIMENSION

    def cache_key(self) -> str:
        return json.dumps(
            {
                "allocation_dimensions": self.allocation_dimensions,
                "as_of": self.as_of,
                "benchmark_id": self.benchmark_id,
                "cache_family": self.cache_family,
                "contract_version": self.contract_version,
                "control_plane_base_url": _safe_base_url_identity(self.control_plane_base_url),
                "environment": self.environment,
                "from_currency": self.from_currency,
                "household_id": self.household_id,
                "instrument_id": self.instrument_id,
                "look_through_mode": self.look_through_mode,
                "mandate_id": self.mandate_id,
                "portfolio_id": self.portfolio_id,
                "query_base_url": _safe_base_url_identity(self.query_base_url),
                "reporting_currency": self.reporting_currency,
                "risk_options": self.risk_options,
                "security_id": self.security_id,
                "taxonomy_scope": self.taxonomy_scope,
                "tenant_id": self.tenant_id,
                "to_currency": self.to_currency,
                "valuation_options": self.valuation_options,
            },
            sort_keys=True,
            separators=(",", ":"),
        )


def stateful_context_cache_key(
    stateful_input: WorkspaceStatefulInput,
    *,
    query_base_url: str = _ABSENT_DIMENSION,
    control_plane_base_url: str = _ABSENT_DIMENSION,
) -> str:
    return _stateful_input_identity(
        stateful_input,
        cache_family="stateful-context",
        query_base_url=query_base_url,
        control_plane_base_url=control_plane_base_url,
    ).cache_key()


def instrument_enrichment_cache_key(
    *,
    control_plane_base_url: str,
    security_id: str,
    portfolio_id: str,
    as_of: str,
) -> str:
    return LotusCoreCacheIdentity(
        cache_family="instrument-enrichment",
        control_plane_base_url=control_plane_base_url,
        portfolio_id=_normalized_dimension(portfolio_id),
        as_of=_normalized_dimension(as_of),
        security_id=_normalized_dimension(security_id),
        environment=_environment_identity(),
        tenant_id=_tenant_identity(),
    ).cache_key()


def classification_taxonomy_cache_key(
    *,
    control_plane_base_url: str,
    as_of: str,
    taxonomy_scope: str,
) -> str:
    return LotusCoreCacheIdentity(
        cache_family="classification-taxonomy",
        control_plane_base_url=control_plane_base_url,
        as_of=_normalized_dimension(as_of),
        taxonomy_scope=_normalized_dimension(taxonomy_scope),
        environment=_environment_identity(),
        tenant_id=_tenant_identity(),
    ).cache_key()


def instrument_lookup_cache_key(
    *,
    query_base_url: str,
    instrument_id: str,
    portfolio_id: str,
    as_of: str,
) -> str:
    return LotusCoreCacheIdentity(
        cache_family="instrument-lookup",
        query_base_url=query_base_url,
        portfolio_id=_normalized_dimension(portfolio_id),
        as_of=_normalized_dimension(as_of),
        instrument_id=_normalized_dimension(instrument_id),
        environment=_environment_identity(),
        tenant_id=_tenant_identity(),
    ).cache_key()


def price_lookup_cache_key(
    *,
    query_base_url: str,
    instrument_id: str,
    portfolio_id: str,
    as_of: str,
) -> str:
    return LotusCoreCacheIdentity(
        cache_family="price-lookup",
        query_base_url=query_base_url,
        portfolio_id=_normalized_dimension(portfolio_id),
        as_of=_normalized_dimension(as_of),
        instrument_id=_normalized_dimension(instrument_id),
        environment=_environment_identity(),
        tenant_id=_tenant_identity(),
    ).cache_key()


def fx_lookup_cache_key(
    *,
    query_base_url: str,
    from_currency: str,
    to_currency: str,
    portfolio_id: str,
    as_of: str,
) -> str:
    return LotusCoreCacheIdentity(
        cache_family="fx-lookup",
        query_base_url=query_base_url,
        portfolio_id=_normalized_dimension(portfolio_id),
        as_of=_normalized_dimension(as_of),
        from_currency=_normalized_dimension(from_currency),
        to_currency=_normalized_dimension(to_currency),
        reporting_currency=_normalized_dimension(to_currency),
        environment=_environment_identity(),
        tenant_id=_tenant_identity(),
    ).cache_key()


def _stateful_input_identity(
    stateful_input: WorkspaceStatefulInput,
    *,
    cache_family: str,
    query_base_url: str,
    control_plane_base_url: str,
) -> LotusCoreCacheIdentity:
    return LotusCoreCacheIdentity(
        cache_family=cache_family,
        query_base_url=query_base_url,
        control_plane_base_url=control_plane_base_url,
        environment=_environment_identity(),
        tenant_id=_tenant_identity(),
        portfolio_id=_normalized_dimension(stateful_input.portfolio_id),
        as_of=_normalized_dimension(stateful_input.as_of),
        reporting_currency=_optional_model_dimension(
            stateful_input,
            "reporting_currency",
            default=_SOURCE_DEFAULT,
        ),
        household_id=_optional_model_dimension(stateful_input, "household_id"),
        mandate_id=_optional_model_dimension(stateful_input, "mandate_id"),
        benchmark_id=_optional_model_dimension(stateful_input, "benchmark_id"),
        look_through_mode=_optional_model_dimension(stateful_input, "look_through_mode"),
        allocation_dimensions=_optional_model_dimension(
            stateful_input,
            "allocation_dimensions",
            default=_SOURCE_DEFAULT,
        ),
        risk_options=_optional_model_dimension(stateful_input, "risk_options"),
    )


def _environment_identity() -> str:
    return _normalized_dimension(os.getenv("ENVIRONMENT", "local").strip().lower())


def _tenant_identity() -> str:
    return _normalized_dimension(os.getenv("LOTUS_ADVISE_TENANT_ID"), default=_TENANT_UNSCOPED)


def _optional_model_dimension(
    value: Any,
    field_name: str,
    *,
    default: str = _ABSENT_DIMENSION,
) -> str:
    return _normalized_dimension(getattr(value, field_name, None), default=default)


def _normalized_dimension(value: Any, *, default: str = _ABSENT_DIMENSION) -> str:
    if value is None:
        return default
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    normalized = str(value).strip()
    return normalized or default


def _safe_base_url_identity(value: str) -> str:
    normalized = _normalized_dimension(value)
    if normalized == _ABSENT_DIMENSION:
        return normalized
    split = urlsplit(normalized)
    if split.hostname is None:
        return normalized.split("?", 1)[0].split("#", 1)[0]
    return urlunsplit(
        (
            split.scheme or "http",
            _netloc_without_credentials(split),
            split.path.rstrip("/"),
            "",
            "",
        )
    )


def _netloc_without_credentials(split: SplitResult) -> str:
    netloc = split.hostname or ""
    if split.port is not None:
        netloc = f"{netloc}:{split.port}"
    return netloc
