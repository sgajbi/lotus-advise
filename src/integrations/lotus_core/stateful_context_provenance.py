from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast

from src.core.source_provenance_models import (
    SourceFreshnessStatus,
    SourceProvenanceEnvelope,
    SourceProvenanceRecord,
)
from src.integrations.lotus_core.context_resolution import LotusCoreContextResolutionError
from src.integrations.lotus_core.contracts import ADVISORY_SIMULATION_CONTRACT_VERSION

_SOURCE_SYSTEM = "LOTUS_CORE"
_FRESHNESS_VALUES: set[SourceFreshnessStatus] = {"CURRENT", "STALE", "PARTIAL", "UNKNOWN"}


@dataclass(frozen=True)
class _SourceIdentity:
    source_id: str
    source_version: str | None
    source_event_id: str | None
    source_batch_id: str | None
    source_hash: str | None
    valuation_timestamp: str | None
    freshness_status: SourceFreshnessStatus


class LotusCoreSourceProvenanceError(LotusCoreContextResolutionError):
    pass


def build_lotus_core_source_provenance(
    *,
    portfolio_id: str,
    resolved_as_of: str,
    portfolio_payload: dict[str, Any],
    positions_payload: dict[str, Any],
    cash_payload: dict[str, Any],
) -> SourceProvenanceEnvelope:
    portfolio = _source_identity(
        source_kind="PORTFOLIO",
        fallback_id=f"lotus-core:portfolio:{portfolio_id}:{resolved_as_of}",
        identity_payloads=(portfolio_payload, positions_payload, cash_payload),
        metadata_payloads=(portfolio_payload,),
        id_keys=("portfolio_snapshot_id", "portfolio_source_snapshot_id"),
        fallback_payload=portfolio_payload,
    )
    market_data = _source_identity(
        source_kind="MARKET_DATA",
        fallback_id=f"lotus-core:market-data:{portfolio_id}:{resolved_as_of}",
        identity_payloads=(positions_payload, cash_payload),
        metadata_payloads=(positions_payload, cash_payload),
        id_keys=("market_data_snapshot_id", "valuation_snapshot_id"),
        fallback_payload=positions_payload,
    )
    return SourceProvenanceEnvelope(
        source_system=_SOURCE_SYSTEM,
        portfolio=_record(
            source_kind="PORTFOLIO",
            identity=portfolio,
            as_of=resolved_as_of,
        ),
        market_data=_record(
            source_kind="MARKET_DATA",
            identity=market_data,
            as_of=resolved_as_of,
        ),
    )


def _source_identity(
    *,
    source_kind: Literal["PORTFOLIO", "MARKET_DATA"],
    fallback_id: str,
    identity_payloads: tuple[dict[str, Any], ...],
    metadata_payloads: tuple[dict[str, Any], ...],
    id_keys: tuple[str, ...],
    fallback_payload: dict[str, Any],
) -> _SourceIdentity:
    source_version = _consistent_payload_text(
        source_kind,
        metadata_payloads,
        keys=("source_version", "snapshot_version", "revision", "revision_id"),
    )
    source_event_id = _consistent_payload_text(
        source_kind,
        metadata_payloads,
        keys=("source_event_id", "event_id", "source_revision_id"),
    )
    source_batch_id = _consistent_payload_text(
        source_kind,
        metadata_payloads,
        keys=("source_batch_id", "batch_id", "ingestion_batch_id"),
    )
    source_hash = _consistent_payload_text(
        source_kind,
        metadata_payloads,
        keys=("source_hash", "content_hash", "snapshot_hash"),
    )
    valuation_timestamp = _consistent_payload_text(
        source_kind,
        metadata_payloads,
        keys=("valuation_timestamp", "valuation_as_of", "source_generated_at", "generated_at"),
    )
    explicit_source_id = _consistent_payload_text(source_kind, identity_payloads, keys=id_keys)
    if explicit_source_id is None:
        explicit_source_id = _normalized_text(fallback_payload.get("snapshot_id"))
    source_id = explicit_source_id or _fallback_source_id(
        fallback_id=fallback_id,
        source_version=source_version,
        source_event_id=source_event_id,
        source_batch_id=source_batch_id,
        source_hash=source_hash,
    )
    return _SourceIdentity(
        source_id=source_id,
        source_version=source_version,
        source_event_id=source_event_id,
        source_batch_id=source_batch_id,
        source_hash=source_hash,
        valuation_timestamp=valuation_timestamp,
        freshness_status=_freshness_status(
            source_kind=source_kind,
            payloads=metadata_payloads,
        ),
    )


def _record(
    *,
    source_kind: Literal["PORTFOLIO", "MARKET_DATA"],
    identity: _SourceIdentity,
    as_of: str,
) -> SourceProvenanceRecord:
    return SourceProvenanceRecord(
        source_system=_SOURCE_SYSTEM,
        source_kind=source_kind,
        source_id=identity.source_id,
        as_of=as_of,
        contract_version=ADVISORY_SIMULATION_CONTRACT_VERSION,
        source_version=identity.source_version,
        source_event_id=identity.source_event_id,
        source_batch_id=identity.source_batch_id,
        source_hash=identity.source_hash,
        valuation_timestamp=identity.valuation_timestamp,
        freshness_status=identity.freshness_status,
    )


def _consistent_payload_text(
    source_kind: Literal["PORTFOLIO", "MARKET_DATA"],
    payloads: tuple[dict[str, Any], ...],
    *,
    keys: tuple[str, ...],
) -> str | None:
    values = {
        value
        for payload in payloads
        for key in keys
        if (value := _normalized_text(payload.get(key))) is not None
    }
    if len(values) > 1:
        raise LotusCoreSourceProvenanceError("LOTUS_CORE_STATEFUL_CONTEXT_INVALID")
    return next(iter(values), None)


def _fallback_source_id(
    *,
    fallback_id: str,
    source_version: str | None,
    source_event_id: str | None,
    source_batch_id: str | None,
    source_hash: str | None,
) -> str:
    for value in (source_version, source_event_id, source_batch_id, source_hash):
        if value is not None:
            return f"{fallback_id}:{value}"
    return fallback_id


def _freshness_status(
    *,
    source_kind: Literal["PORTFOLIO", "MARKET_DATA"],
    payloads: tuple[dict[str, Any], ...],
) -> SourceFreshnessStatus:
    value = _consistent_payload_text(
        source_kind,
        payloads,
        keys=("freshness_status", "valuation_freshness_status"),
    )
    if value is None:
        return "UNKNOWN"
    normalized = value.upper()
    if normalized not in _FRESHNESS_VALUES:
        return "UNKNOWN"
    return cast(SourceFreshnessStatus, normalized)


def _normalized_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


__all__ = [
    "LotusCoreSourceProvenanceError",
    "build_lotus_core_source_provenance",
]
