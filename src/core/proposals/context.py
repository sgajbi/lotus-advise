from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, cast

from src.core.models import ProposalSimulateRequest
from src.core.proposals.models import (
    ProposalCreateMetadata,
    ProposalCreateRequest,
    ProposalInputMode,
    ProposalResolvedContext,
    ProposalSimulationRequest,
    ProposalStatefulInput,
    ProposalVersionRequest,
)
from src.integrations.lotus_core import (
    LotusCoreContextResolutionError,
    resolve_lotus_core_advisory_context,
)


class ProposalContextResolutionError(Exception):
    pass


@dataclass(frozen=True)
class ResolvedProposalContext:
    input_mode: ProposalInputMode
    resolution_source: str
    simulate_request: ProposalSimulateRequest
    resolved_context: ProposalResolvedContext
    metadata: ProposalCreateMetadata
    used_legacy_contract: bool


@dataclass(frozen=True)
class ResolvedSimulationContext:
    input_mode: ProposalInputMode
    resolution_source: str
    simulate_request: ProposalSimulateRequest
    resolved_context: ProposalResolvedContext
    used_legacy_contract: bool


def _current_business_date_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _build_resolved_context_from_simulate_request(
    simulate_request: ProposalSimulateRequest,
) -> ProposalResolvedContext:
    return ProposalResolvedContext(
        portfolio_id=simulate_request.portfolio_snapshot.portfolio_id,
        as_of=simulate_request.reference_model.as_of
        if simulate_request.reference_model is not None
        else _current_business_date_iso(),
        portfolio_snapshot_id=simulate_request.portfolio_snapshot.snapshot_id,
        market_data_snapshot_id=simulate_request.market_data_snapshot.snapshot_id,
    )


def _metadata_with_stateful_defaults(
    metadata: ProposalCreateMetadata,
    stateful_input: ProposalStatefulInput | None,
) -> ProposalCreateMetadata:
    if stateful_input is None or metadata.mandate_id is not None:
        return cast(ProposalCreateMetadata, metadata.model_copy(deep=True))
    return cast(
        ProposalCreateMetadata,
        metadata.model_copy(update={"mandate_id": stateful_input.mandate_id}),
    )


def _resolve_stateful_input(
    stateful_input: ProposalStatefulInput,
) -> tuple[ProposalSimulateRequest, ProposalResolvedContext]:
    try:
        resolved = resolve_lotus_core_advisory_context(stateful_input)
    except LotusCoreContextResolutionError as exc:
        raise ProposalContextResolutionError(
            "PROPOSAL_STATEFUL_CONTEXT_RESOLUTION_UNAVAILABLE"
        ) from exc

    return (
        resolved.simulate_request,
        ProposalResolvedContext.model_validate(resolved.resolved_context.model_dump(mode="json")),
    )


def resolve_create_request(payload: ProposalCreateRequest) -> ResolvedProposalContext:
    if payload.input_mode == "stateful":
        assert payload.stateful_input is not None
        simulate_request, resolved_context = _resolve_stateful_input(payload.stateful_input)
        return ResolvedProposalContext(
            input_mode="stateful",
            resolution_source="LOTUS_CORE",
            simulate_request=simulate_request,
            resolved_context=resolved_context,
            metadata=_metadata_with_stateful_defaults(payload.metadata, payload.stateful_input),
            used_legacy_contract=False,
        )

    if payload.input_mode == "stateless":
        assert payload.stateless_input is not None
        simulate_request = payload.stateless_input.simulate_request.model_copy(deep=True)
        return ResolvedProposalContext(
            input_mode="stateless",
            resolution_source="DIRECT_REQUEST",
            simulate_request=simulate_request,
            resolved_context=_build_resolved_context_from_simulate_request(simulate_request),
            metadata=payload.metadata.model_copy(deep=True),
            used_legacy_contract=False,
        )

    assert payload.simulate_request is not None
    simulate_request = payload.simulate_request.model_copy(deep=True)
    return ResolvedProposalContext(
        input_mode="stateless",
        resolution_source="DIRECT_REQUEST",
        simulate_request=simulate_request,
        resolved_context=_build_resolved_context_from_simulate_request(simulate_request),
        metadata=payload.metadata.model_copy(deep=True),
        used_legacy_contract=True,
    )


def resolve_simulation_request(payload: ProposalSimulationRequest) -> ResolvedSimulationContext:
    if payload.input_mode == "stateful":
        assert payload.stateful_input is not None
        simulate_request, resolved_context = _resolve_stateful_input(payload.stateful_input)
        return ResolvedSimulationContext(
            input_mode="stateful",
            resolution_source="LOTUS_CORE",
            simulate_request=simulate_request,
            resolved_context=resolved_context,
            used_legacy_contract=False,
        )

    if payload.input_mode == "stateless":
        assert payload.stateless_input is not None
        simulate_request = payload.stateless_input.simulate_request.model_copy(deep=True)
        return ResolvedSimulationContext(
            input_mode="stateless",
            resolution_source="DIRECT_REQUEST",
            simulate_request=simulate_request,
            resolved_context=_build_resolved_context_from_simulate_request(simulate_request),
            used_legacy_contract=False,
        )

    assert payload.simulate_request is not None
    simulate_request = payload.simulate_request.model_copy(deep=True)
    return ResolvedSimulationContext(
        input_mode="stateless",
        resolution_source="DIRECT_REQUEST",
        simulate_request=simulate_request,
        resolved_context=_build_resolved_context_from_simulate_request(simulate_request),
        used_legacy_contract=True,
    )


def resolve_version_request(payload: ProposalVersionRequest) -> ResolvedProposalContext:
    metadata = ProposalCreateMetadata()
    if payload.input_mode == "stateful":
        assert payload.stateful_input is not None
        simulate_request, resolved_context = _resolve_stateful_input(payload.stateful_input)
        return ResolvedProposalContext(
            input_mode="stateful",
            resolution_source="LOTUS_CORE",
            simulate_request=simulate_request,
            resolved_context=resolved_context,
            metadata=_metadata_with_stateful_defaults(metadata, payload.stateful_input),
            used_legacy_contract=False,
        )

    if payload.input_mode == "stateless":
        assert payload.stateless_input is not None
        simulate_request = payload.stateless_input.simulate_request.model_copy(deep=True)
        return ResolvedProposalContext(
            input_mode="stateless",
            resolution_source="DIRECT_REQUEST",
            simulate_request=simulate_request,
            resolved_context=_build_resolved_context_from_simulate_request(simulate_request),
            metadata=metadata,
            used_legacy_contract=False,
        )

    assert payload.simulate_request is not None
    simulate_request = payload.simulate_request.model_copy(deep=True)
    return ResolvedProposalContext(
        input_mode="stateless",
        resolution_source="DIRECT_REQUEST",
        simulate_request=simulate_request,
        resolved_context=_build_resolved_context_from_simulate_request(simulate_request),
        metadata=metadata,
        used_legacy_contract=True,
    )


def canonicalize_create_request_payload(
    *,
    payload: ProposalCreateRequest,
    resolved: ResolvedProposalContext,
) -> dict[str, Any]:
    return {
        "created_by": payload.created_by,
        "metadata": resolved.metadata.model_dump(mode="json"),
        "advisory_context": {
            "input_mode": resolved.input_mode,
            "resolution_source": resolved.resolution_source,
            "resolved_context": resolved.resolved_context.model_dump(mode="json"),
            "simulate_request": resolved.simulate_request.model_dump(mode="json"),
        },
    }


def canonicalize_simulation_request_payload(
    *,
    resolved: ResolvedSimulationContext,
) -> dict[str, Any]:
    return {
        "advisory_context": {
            "input_mode": resolved.input_mode,
            "resolution_source": resolved.resolution_source,
            "resolved_context": resolved.resolved_context.model_dump(mode="json"),
            "simulate_request": resolved.simulate_request.model_dump(mode="json"),
        }
    }


def canonicalize_version_request_payload(
    *,
    payload: ProposalVersionRequest,
    resolved: ResolvedProposalContext,
) -> dict[str, Any]:
    return {
        "created_by": payload.created_by,
        "expected_current_version_no": payload.expected_current_version_no,
        "advisory_context": {
            "input_mode": resolved.input_mode,
            "resolution_source": resolved.resolution_source,
            "resolved_context": resolved.resolved_context.model_dump(mode="json"),
            "simulate_request": resolved.simulate_request.model_dump(mode="json"),
        },
    }


def build_context_resolution_evidence(
    resolved: ResolvedProposalContext | ResolvedSimulationContext,
) -> dict[str, Any]:
    return {
        "input_mode": resolved.input_mode,
        "resolution_source": resolved.resolution_source,
        "used_legacy_contract": resolved.used_legacy_contract,
        "resolved_context": resolved.resolved_context.model_dump(mode="json"),
    }
