from __future__ import annotations

import argparse
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Literal, cast

import httpx

_DEFAULT_ADVISE_BASE_URL = "http://advise.dev.lotus"
_DEFAULT_CORE_QUERY_BASE_URL = "http://core-query.dev.lotus"
_DEFAULT_RISK_BASE_URL = "http://risk.dev.lotus"
_DEFAULT_PORTFOLIO_CANDIDATES = (
    "DEMO_ADV_USD_001",
    "PB_SG_GLOBAL_BAL_001",
    "DEMO_REBAL_USD_001",
    "DEMO_INCOME_CHF_001",
)
_PROPOSAL_ALLOCATION_DIMENSIONS = [
    "asset_class",
    "currency",
    "sector",
    "country",
    "region",
    "product_type",
    "rating",
]
_WARM_CACHE_TOLERANCE_MULTIPLIER = 1.75
_WARM_CACHE_TOLERANCE_ABSOLUTE_MS = 125.0


class LiveParityValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class PortfolioParityScenario:
    portfolio_id: str
    as_of_date: str
    reporting_currency: str
    issuer_coverage_status: str
    risk_available: bool


@dataclass(frozen=True)
class LiveParityResult:
    complete_issuer_portfolio: str
    degraded_issuer_portfolio: str
    degraded_issuer_coverage_status: str
    cold_duration_ms: float
    warm_duration_ms: float
    workspace_handoff_portfolio: str
    lifecycle_portfolio: str
    lifecycle_latest_version_no: int
    lifecycle_current_state: str
    async_lifecycle_portfolio: str
    async_lifecycle_latest_version_no: int
    async_lifecycle_current_state: str
    execution_handoff_status: str
    execution_terminal_status: str
    report_status: str


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise LiveParityValidationError(message)


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _utc_iso_after(*, seconds: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _request_json(
    client: httpx.Client,
    *,
    method: str,
    url: str,
    expected_status: int,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    response = client.request(method, url, json=json_body, headers=headers)
    _assert(
        response.status_code == expected_status,
        (
            f"{method} {url}: expected HTTP {expected_status}, "
            f"got {response.status_code}, body={response.text}"
        ),
    )
    payload = cast(dict[str, Any], response.json())
    _assert(isinstance(payload, dict), f"{method} {url}: expected JSON object payload")
    return payload


def _normalize_allocation_views(views: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    normalized: dict[str, dict[str, Any]] = {}
    for view in views:
        dimension = str(view["dimension"])
        if "total_market_value_reporting_currency" in view:
            total = _decimal(view["total_market_value_reporting_currency"])
            buckets = [
                {
                    "value": str(bucket["dimension_value"]),
                    "market_value": _decimal(bucket["market_value_reporting_currency"]),
                    "weight": _decimal(bucket["weight"]),
                    "position_count": int(bucket["position_count"]),
                }
                for bucket in view["buckets"]
            ]
        else:
            total = _decimal(view["total_value"]["amount"])
            buckets = [
                {
                    "value": str(bucket["key"]),
                    "market_value": _decimal(bucket["value"]["amount"]),
                    "weight": _decimal(bucket["weight"]),
                    "position_count": int(bucket["position_count"]),
                }
                for bucket in view["buckets"]
            ]
        normalized[dimension] = {
            "total": total,
            "buckets": buckets,
        }
    return normalized


def _normalize_risk_payload(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata") or {}
    valuation_context = payload.get("valuation_context") or {}
    return {
        "source_service": payload["source_service"],
        "input_mode": payload["input_mode"],
        "risk_proxy": dict(payload["risk_proxy"]),
        "single_position_concentration": dict(payload["single_position_concentration"]),
        "issuer_concentration": dict(payload["issuer_concentration"]),
        "valuation_context": dict(valuation_context),
        "metadata": {
            "portfolio_id": metadata.get("portfolio_id"),
            "as_of_date": metadata.get("as_of_date"),
        },
    }


def _feature_by_key(capabilities: dict[str, Any], key: str) -> dict[str, Any]:
    features = capabilities.get("features")
    _assert(isinstance(features, list), "/platform/capabilities: features must be a list")
    feature_list = cast(list[Any], features)
    for feature in feature_list:
        if isinstance(feature, dict) and feature.get("key") == key:
            return cast(dict[str, Any], feature)
    raise LiveParityValidationError(f"/platform/capabilities: missing feature {key}")


def _resolve_latest_portfolio_context(
    client: httpx.Client,
    *,
    core_query_base_url: str,
    portfolio_id: str,
) -> tuple[str, str]:
    payload = _request_json(
        client,
        method="POST",
        url=f"{core_query_base_url}/reporting/portfolio-summary/query",
        expected_status=200,
        json_body={"portfolio_id": portfolio_id},
    )
    return str(payload["resolved_as_of_date"]), str(payload["reporting_currency"])


def _stateful_noop_request(*, portfolio_id: str, as_of_date: str) -> dict[str, Any]:
    return {
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": portfolio_id,
            "as_of": as_of_date,
        },
    }


def _simulate_stateful_noop(
    client: httpx.Client,
    *,
    advise_base_url: str,
    portfolio_id: str,
    as_of_date: str,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    return _request_json(
        client,
        method="POST",
        url=f"{advise_base_url}/advisory/proposals/simulate",
        expected_status=200,
        json_body=_stateful_noop_request(portfolio_id=portfolio_id, as_of_date=as_of_date),
        headers={"Idempotency-Key": idempotency_key or f"live-parity-{uuid.uuid4().hex}"},
    )


def _query_live_allocation(
    client: httpx.Client,
    *,
    core_query_base_url: str,
    portfolio_id: str,
    as_of_date: str,
    reporting_currency: str,
) -> dict[str, Any]:
    return _request_json(
        client,
        method="POST",
        url=f"{core_query_base_url}/reporting/asset-allocation/query",
        expected_status=200,
        json_body={
            "scope": {"portfolio_id": portfolio_id},
            "as_of_date": as_of_date,
            "reporting_currency": reporting_currency,
            "dimensions": _PROPOSAL_ALLOCATION_DIMENSIONS,
            "look_through_mode": "direct_only",
        },
    )


def _query_direct_concentration(
    client: httpx.Client,
    *,
    risk_base_url: str,
    portfolio_id: str,
    as_of_date: str,
    reporting_currency: str,
) -> dict[str, Any]:
    return _request_json(
        client,
        method="POST",
        url=f"{risk_base_url}/analytics/risk/concentration",
        expected_status=200,
        json_body={
            "input_mode": "simulation",
            "simulation_input": {
                "portfolio_id": portfolio_id,
                "as_of_date": as_of_date,
                "reporting_currency": reporting_currency,
                "include_cash_positions": True,
                "include_zero_quantity_positions": False,
                "top_n": 10,
                "simulation_changes": [],
            },
            "issuer_grouping_level": "ultimate_parent",
            "enrichment_policy": "merge_caller_then_core",
        },
    )


def _select_scenarios(
    client: httpx.Client,
    *,
    advise_base_url: str,
    core_query_base_url: str,
    candidates: tuple[str, ...],
) -> tuple[PortfolioParityScenario, PortfolioParityScenario]:
    complete: PortfolioParityScenario | None = None
    degraded: PortfolioParityScenario | None = None
    examined: list[tuple[str, str]] = []

    for portfolio_id in candidates:
        as_of_date, reporting_currency = _resolve_latest_portfolio_context(
            client,
            core_query_base_url=core_query_base_url,
            portfolio_id=portfolio_id,
        )
        simulate = _simulate_stateful_noop(
            client,
            advise_base_url=advise_base_url,
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
        )
        authority = simulate.get("explanation", {}).get("authority_resolution") or {}
        risk_lens = simulate.get("explanation", {}).get("risk_lens")
        risk_available = isinstance(risk_lens, dict)
        coverage_status = (
            str(risk_lens["issuer_concentration"]["coverage_status"])
            if risk_available
            else "unavailable"
        )
        examined.append((portfolio_id, coverage_status))
        scenario = PortfolioParityScenario(
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            reporting_currency=reporting_currency,
            issuer_coverage_status=coverage_status,
            risk_available=risk_available,
        )
        if risk_available and coverage_status == "complete" and complete is None:
            complete = scenario
        elif coverage_status in {"partial", "unavailable"} and degraded is None:
            degraded = scenario
        elif (
            coverage_status == "partial"
            and degraded is not None
            and degraded.issuer_coverage_status != "partial"
        ):
            degraded = scenario
        elif (
            not risk_available
            and authority.get("risk_authority") == "unavailable"
            and degraded is None
        ):
            degraded = scenario
        if complete is not None and degraded is not None:
            return complete, degraded

    raise LiveParityValidationError(
        "Could not find both complete and degraded issuer-coverage parity scenarios from seeded "
        f"portfolios. examined={examined}"
    )


def _assert_allocation_parity(
    *,
    scenario: PortfolioParityScenario,
    direct_allocation: dict[str, Any],
    proposal_body: dict[str, Any],
) -> None:
    direct_views = _normalize_allocation_views(direct_allocation["views"])
    before_views = _normalize_allocation_views(proposal_body["before"]["allocation_views"])
    after_views = _normalize_allocation_views(proposal_body["after_simulated"]["allocation_views"])

    _assert(
        direct_views == before_views,
        (
            f"{scenario.portfolio_id}: proposal before allocation views diverged "
            "from live lotus-core allocation"
        ),
    )
    _assert(
        direct_views == after_views,
        (
            f"{scenario.portfolio_id}: no-op proposal after allocation views diverged "
            "from live lotus-core allocation"
        ),
    )


def _assert_authority_posture(
    *,
    scenario: PortfolioParityScenario,
    proposal_body: dict[str, Any],
) -> None:
    authority_resolution = proposal_body.get("explanation", {}).get("authority_resolution")
    _assert(
        isinstance(authority_resolution, dict),
        f"{scenario.portfolio_id}: proposal response missing authority_resolution",
    )
    _assert(
        authority_resolution.get("simulation_authority") == "lotus_core",
        (
            f"{scenario.portfolio_id}: expected lotus_core simulation authority, got "
            f"{authority_resolution}"
        ),
    )
    _assert(
        authority_resolution.get("risk_authority") == "lotus_risk",
        (
            f"{scenario.portfolio_id}: expected lotus_risk risk authority, got "
            f"{authority_resolution}"
        ),
    )
    _assert(
        authority_resolution.get("degraded") is False,
        (
            f"{scenario.portfolio_id}: proposal response unexpectedly degraded on live parity "
            f"path: {authority_resolution}"
        ),
    )


def _assert_risk_parity(
    *,
    scenario: PortfolioParityScenario,
    direct_risk: dict[str, Any],
    proposal_body: dict[str, Any],
) -> None:
    direct_normalized = _normalize_risk_payload(direct_risk)
    proposal_normalized = _normalize_risk_payload(proposal_body["explanation"]["risk_lens"])
    _assert(
        direct_normalized == proposal_normalized,
        (
            f"{scenario.portfolio_id}: proposal risk_lens diverged from direct "
            "lotus-risk concentration"
        ),
    )


def _measure_warm_cache(
    client: httpx.Client,
    *,
    advise_base_url: str,
    scenario: PortfolioParityScenario,
) -> tuple[float, float]:
    def _timed_call() -> tuple[dict[str, Any], float]:
        started = time.perf_counter()
        body = _simulate_stateful_noop(
            client,
            advise_base_url=advise_base_url,
            portfolio_id=scenario.portfolio_id,
            as_of_date=scenario.as_of_date,
        )
        return body, (time.perf_counter() - started) * 1000.0

    cold_body, cold_ms = _timed_call()
    warm_body, warm_ms = _timed_call()
    _assert(
        _normalize_allocation_views(cold_body["before"]["allocation_views"])
        == _normalize_allocation_views(warm_body["before"]["allocation_views"]),
        f"{scenario.portfolio_id}: repeated stateful simulate changed before allocation views",
    )
    warm_threshold_ms = max(
        cold_ms * _WARM_CACHE_TOLERANCE_MULTIPLIER,
        cold_ms + _WARM_CACHE_TOLERANCE_ABSOLUTE_MS,
    )
    _assert(
        warm_ms <= warm_threshold_ms,
        (
            f"{scenario.portfolio_id}: warm cache regression detected "
            f"cold_ms={cold_ms:.2f} warm_ms={warm_ms:.2f} "
            f"threshold_ms={warm_threshold_ms:.2f}"
        ),
    )
    return cold_ms, warm_ms


def _post_json(
    client: httpx.Client,
    *,
    url: str,
    expected_status: int,
    json_body: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    return _request_json(
        client,
        method="POST",
        url=url,
        expected_status=expected_status,
        json_body=json_body,
        headers=headers,
    )


def _get_json(
    client: httpx.Client,
    *,
    url: str,
    expected_status: int,
) -> dict[str, Any]:
    return _request_json(
        client,
        method="GET",
        url=url,
        expected_status=expected_status,
    )


def _create_stateful_proposal(
    client: httpx.Client,
    *,
    advise_base_url: str,
    scenario: PortfolioParityScenario,
    created_by: str,
) -> dict[str, Any]:
    return _post_json(
        client,
        url=f"{advise_base_url}/advisory/proposals",
        expected_status=200,
        json_body={
            "created_by": created_by,
            "input_mode": "stateful",
            "stateful_input": {
                "portfolio_id": scenario.portfolio_id,
                "as_of": scenario.as_of_date,
            },
        },
        headers={"Idempotency-Key": f"live-create-{uuid.uuid4().hex}"},
    )


def _create_stateful_version(
    client: httpx.Client,
    *,
    advise_base_url: str,
    proposal_id: str,
    scenario: PortfolioParityScenario,
    created_by: str,
    expected_current_version_no: int,
) -> dict[str, Any]:
    return _post_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}/versions",
        expected_status=200,
        json_body={
            "created_by": created_by,
            "expected_current_version_no": expected_current_version_no,
            "input_mode": "stateful",
            "stateful_input": {
                "portfolio_id": scenario.portfolio_id,
                "as_of": scenario.as_of_date,
            },
        },
    )


def _submit_async_create(
    client: httpx.Client,
    *,
    advise_base_url: str,
    scenario: PortfolioParityScenario,
    created_by: str,
) -> dict[str, Any]:
    return _post_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/async",
        expected_status=202,
        json_body={
            "created_by": created_by,
            "input_mode": "stateful",
            "stateful_input": {
                "portfolio_id": scenario.portfolio_id,
                "as_of": scenario.as_of_date,
            },
        },
        headers={
            "Idempotency-Key": f"live-async-create-{uuid.uuid4().hex}",
            "X-Correlation-Id": f"live-async-create-{uuid.uuid4().hex}",
        },
    )


def _submit_async_version(
    client: httpx.Client,
    *,
    advise_base_url: str,
    proposal_id: str,
    scenario: PortfolioParityScenario,
    created_by: str,
    expected_current_version_no: int,
) -> dict[str, Any]:
    return _post_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}/versions/async",
        expected_status=202,
        json_body={
            "created_by": created_by,
            "expected_current_version_no": expected_current_version_no,
            "input_mode": "stateful",
            "stateful_input": {
                "portfolio_id": scenario.portfolio_id,
                "as_of": scenario.as_of_date,
            },
        },
        headers={"X-Correlation-Id": f"live-async-version-{uuid.uuid4().hex}"},
    )


def _wait_for_async_success(
    client: httpx.Client,
    *,
    advise_base_url: str,
    operation_id: str,
    expected_type: str,
) -> dict[str, Any]:
    deadline = time.monotonic() + 45.0
    while time.monotonic() < deadline:
        status_body = _get_json(
            client,
            url=f"{advise_base_url}/advisory/proposals/operations/{operation_id}",
            expected_status=200,
        )
        _assert(
            status_body["operation_type"] == expected_type,
            f"{operation_id}: unexpected operation type {status_body['operation_type']}",
        )
        if status_body["status"] == "SUCCEEDED":
            result = status_body.get("result")
            _assert(isinstance(result, dict), f"{operation_id}: async success missing result")
            return cast(dict[str, Any], result)
        if status_body["status"] == "FAILED":
            raise LiveParityValidationError(
                f"{operation_id}: async operation failed {status_body.get('error')}"
            )
        time.sleep(0.5)
    raise LiveParityValidationError(f"{operation_id}: async operation did not finish in time")


def _assert_async_operation_surfaces(
    client: httpx.Client,
    *,
    advise_base_url: str,
    accepted_body: dict[str, Any],
    expected_type: str,
    result_body: dict[str, Any],
) -> None:
    operation_id = str(accepted_body["operation_id"])
    correlation_id = str(accepted_body["correlation_id"])
    operation = _get_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/operations/{operation_id}",
        expected_status=200,
    )
    by_correlation = _get_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/operations/by-correlation/{correlation_id}",
        expected_status=200,
    )
    replay = _get_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/operations/{operation_id}/replay-evidence",
        expected_status=200,
    )
    proposal = cast(dict[str, Any], result_body["proposal"])
    version = cast(dict[str, Any], result_body["version"])
    proposal_id = str(proposal["proposal_id"])
    version_no = int(version["version_no"])
    version_replay = _get_json(
        client,
        url=(
            f"{advise_base_url}/advisory/proposals/{proposal_id}/versions/"
            f"{version_no}/replay-evidence"
        ),
        expected_status=200,
    )
    detail = _get_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}?include_evidence=false",
        expected_status=200,
    )

    _assert(
        operation["operation_type"] == by_correlation["operation_type"] == expected_type,
        f"{operation_id}: async operation type diverged across read surfaces",
    )
    _assert(
        operation["operation_id"] == by_correlation["operation_id"] == operation_id,
        f"{operation_id}: operation lookup diverged across id/correlation surfaces",
    )
    _assert(
        operation["correlation_id"] == by_correlation["correlation_id"] == correlation_id,
        f"{operation_id}: correlation lookup diverged across id/correlation surfaces",
    )
    _assert(
        operation["status"] == by_correlation["status"] == "SUCCEEDED",
        f"{operation_id}: async operation did not stay in succeeded state",
    )
    _assert(
        str(cast(dict[str, Any], operation["result"])["proposal"]["proposal_id"]) == proposal_id,
        f"{operation_id}: operation result proposal id diverged from async result",
    )
    _assert(
        int(cast(dict[str, Any], operation["result"])["version"]["version_no"]) == version_no,
        f"{operation_id}: operation result version diverged from async result",
    )
    _assert(
        replay["subject"]["scope"] == "ASYNC_OPERATION",
        f"{operation_id}: async replay subject scope was not ASYNC_OPERATION",
    )
    _assert(
        replay["subject"]["operation_id"] == operation_id,
        f"{operation_id}: async replay subject lost operation id",
    )
    _assert(
        replay["subject"]["proposal_id"] == proposal_id,
        f"{operation_id}: async replay subject lost proposal id",
    )
    _assert(
        replay["subject"]["proposal_version_no"] == version_no,
        f"{operation_id}: async replay subject lost proposal version",
    )
    _assert(
        replay["continuity"]["correlation_id"] == correlation_id,
        f"{operation_id}: async replay continuity lost correlation id",
    )
    _assert(
        replay["continuity"]["async_operation_id"] == operation_id,
        f"{operation_id}: async replay continuity lost operation id",
    )
    _assert(
        replay["hashes"]["request_hash"] == version_replay["hashes"]["request_hash"],
        f"{operation_id}: async/proposal replay request hash diverged",
    )
    _assert(
        replay["hashes"]["simulation_hash"] == version_replay["hashes"]["simulation_hash"],
        f"{operation_id}: async/proposal replay simulation hash diverged",
    )
    _assert(
        replay["resolved_context"] == version_replay["resolved_context"],
        f"{operation_id}: async/proposal replay resolved context diverged",
    )
    _assert(
        int(detail["proposal"]["current_version_no"]) >= version_no,
        f"{operation_id}: proposal detail current version regressed behind async result",
    )


def _post_transition(
    client: httpx.Client,
    *,
    advise_base_url: str,
    proposal_id: str,
    event_type: str,
    actor_id: str,
    expected_state: str,
    related_version_no: int,
    reason: dict[str, Any],
) -> dict[str, Any]:
    return _post_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}/transitions",
        expected_status=200,
        json_body={
            "event_type": event_type,
            "actor_id": actor_id,
            "expected_state": expected_state,
            "related_version_no": related_version_no,
            "reason": reason,
        },
    )


def _post_approval(
    client: httpx.Client,
    *,
    advise_base_url: str,
    proposal_id: str,
    approval_type: str,
    actor_id: str,
    expected_state: str,
    related_version_no: int,
    details: dict[str, Any],
) -> dict[str, Any]:
    return _post_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}/approvals",
        expected_status=200,
        json_body={
            "approval_type": approval_type,
            "approved": True,
            "actor_id": actor_id,
            "expected_state": expected_state,
            "related_version_no": related_version_no,
            "details": details,
        },
    )


def _promote_to_execution_ready(
    client: httpx.Client,
    *,
    advise_base_url: str,
    proposal_id: str,
    related_version_no: int,
    route: Literal["risk", "compliance"] = "risk",
) -> None:
    current_state = "DRAFT"
    if current_state == "DRAFT":
        route_event_type = (
            "SUBMITTED_FOR_RISK_REVIEW"
            if route == "risk"
            else "SUBMITTED_FOR_COMPLIANCE_REVIEW"
        )
        route_target_state = "RISK_REVIEW" if route == "risk" else "COMPLIANCE_REVIEW"
        transition = _post_transition(
            client,
            advise_base_url=advise_base_url,
            proposal_id=proposal_id,
            event_type=route_event_type,
            actor_id="live-parity-validator",
            expected_state="DRAFT",
            related_version_no=related_version_no,
            reason={"comment": "live delivery validation"},
        )
        current_state = str(transition["current_state"])
        _assert(
            current_state == route_target_state,
            f"{proposal_id}: unexpected state after {route} submission {current_state}",
        )
    if current_state == "RISK_REVIEW":
        approval = _post_approval(
            client,
            advise_base_url=advise_base_url,
            proposal_id=proposal_id,
            approval_type="RISK",
            actor_id="risk-approver",
            expected_state="RISK_REVIEW",
            related_version_no=related_version_no,
            details={"channel": "LIVE_VALIDATOR"},
        )
        current_state = str(approval["current_state"])
    if current_state == "COMPLIANCE_REVIEW":
        approval = _post_approval(
            client,
            advise_base_url=advise_base_url,
            proposal_id=proposal_id,
            approval_type="COMPLIANCE",
            actor_id="compliance-approver",
            expected_state="COMPLIANCE_REVIEW",
            related_version_no=related_version_no,
            details={"channel": "LIVE_VALIDATOR"},
        )
        current_state = str(approval["current_state"])
    if current_state == "AWAITING_CLIENT_CONSENT":
        approval = _post_approval(
            client,
            advise_base_url=advise_base_url,
            proposal_id=proposal_id,
            approval_type="CLIENT_CONSENT",
            actor_id="client-consent",
            expected_state="AWAITING_CLIENT_CONSENT",
            related_version_no=related_version_no,
            details={"channel": "LIVE_VALIDATOR"},
        )
        current_state = str(approval["current_state"])
    _assert(
        current_state == "EXECUTION_READY",
        f"{proposal_id}: could not promote proposal to execution ready, final={current_state}",
    )


def _assert_mixed_approval_routes_remain_version_scoped(
    client: httpx.Client,
    *,
    advise_base_url: str,
    scenario: PortfolioParityScenario,
) -> None:
    created = _create_stateful_proposal(
        client,
        advise_base_url=advise_base_url,
        scenario=scenario,
        created_by="live-parity-validator-route-scope",
    )
    proposal_id = str(created["proposal"]["proposal_id"])
    _promote_to_execution_ready(
        client,
        advise_base_url=advise_base_url,
        proposal_id=proposal_id,
        related_version_no=1,
        route="compliance",
    )

    version_created = _create_stateful_version(
        client,
        advise_base_url=advise_base_url,
        proposal_id=proposal_id,
        scenario=scenario,
        created_by="live-parity-validator-route-scope-version",
        expected_current_version_no=1,
    )
    _assert(
        version_created["proposal"]["current_state"] == "DRAFT",
        f"{proposal_id}: mixed-route scope version did not reset to DRAFT",
    )
    _promote_to_execution_ready(
        client,
        advise_base_url=advise_base_url,
        proposal_id=proposal_id,
        related_version_no=2,
        route="risk",
    )
    approvals = _get_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}/approvals",
        expected_status=200,
    )
    timeline = _get_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}/workflow-events",
        expected_status=200,
    )
    approval_rows = cast(list[dict[str, Any]], approvals["approvals"])
    timeline_events = cast(list[dict[str, Any]], timeline["events"])
    _assert(
        {str(approval["approval_type"]) for approval in approval_rows}
        == {"COMPLIANCE", "RISK", "CLIENT_CONSENT"},
        f"{proposal_id}: approvals endpoint lost mixed-route approval lineage",
    )
    _assert(
        {int(approval["related_version_no"]) for approval in approval_rows} == {1, 2},
        f"{proposal_id}: approvals endpoint lost mixed-route version lineage",
    )
    _assert(
        any(
            event["event_type"] == "COMPLIANCE_APPROVED" and int(event["related_version_no"]) == 1
            for event in timeline_events
        )
        and any(
            event["event_type"] == "RISK_APPROVED" and int(event["related_version_no"]) == 2
            for event in timeline_events
        ),
        f"{proposal_id}: workflow timeline lost mixed-route approval lineage",
    )


def _assert_lifecycle_and_delivery_flow(
    client: httpx.Client,
    *,
    advise_base_url: str,
    scenario: PortfolioParityScenario,
) -> tuple[str, int, str, str, str]:
    created = _create_stateful_proposal(
        client,
        advise_base_url=advise_base_url,
        scenario=scenario,
        created_by="live-parity-validator",
    )
    proposal = created["proposal"]
    version = created["version"]
    proposal_id = str(proposal["proposal_id"])
    related_version_no = int(version["version_no"])
    _assert_authority_posture(scenario=scenario, proposal_body=version["proposal_result"])

    version_created = _create_stateful_version(
        client,
        advise_base_url=advise_base_url,
        proposal_id=proposal_id,
        scenario=scenario,
        created_by="live-parity-validator-version",
        expected_current_version_no=related_version_no,
    )
    _assert(
        int(version_created["proposal"]["current_version_no"]) == related_version_no + 1,
        f"{proposal_id}: new version did not increment current_version_no",
    )
    related_version_no = int(version_created["proposal"]["current_version_no"])
    _assert_authority_posture(
        scenario=scenario,
        proposal_body=version_created["version"]["proposal_result"],
    )

    async_created = _submit_async_create(
        client,
        advise_base_url=advise_base_url,
        scenario=scenario,
        created_by="live-parity-validator-async",
    )
    async_create_result = _wait_for_async_success(
        client,
        advise_base_url=advise_base_url,
        operation_id=str(async_created["operation_id"]),
        expected_type="CREATE_PROPOSAL",
    )
    _assert_async_operation_surfaces(
        client,
        advise_base_url=advise_base_url,
        accepted_body=async_created,
        expected_type="CREATE_PROPOSAL",
        result_body=async_create_result,
    )
    async_proposal = async_create_result["proposal"]
    async_version = async_create_result["version"]
    async_proposal_id = str(async_proposal["proposal_id"])
    async_version_no = int(async_version["version_no"])
    _assert_authority_posture(scenario=scenario, proposal_body=async_version["proposal_result"])

    async_version_created = _submit_async_version(
        client,
        advise_base_url=advise_base_url,
        proposal_id=async_proposal_id,
        scenario=scenario,
        created_by="live-parity-validator-async-version",
        expected_current_version_no=async_version_no,
    )
    async_version_result = _wait_for_async_success(
        client,
        advise_base_url=advise_base_url,
        operation_id=str(async_version_created["operation_id"]),
        expected_type="CREATE_PROPOSAL_VERSION",
    )
    _assert_async_operation_surfaces(
        client,
        advise_base_url=advise_base_url,
        accepted_body=async_version_created,
        expected_type="CREATE_PROPOSAL_VERSION",
        result_body=async_version_result,
    )
    _assert(
        int(async_version_result["proposal"]["current_version_no"]) == async_version_no + 1,
        f"{async_proposal_id}: async version did not increment current_version_no",
    )
    _assert_authority_posture(
        scenario=scenario,
        proposal_body=async_version_result["version"]["proposal_result"],
    )

    _promote_to_execution_ready(
        client,
        advise_base_url=advise_base_url,
        proposal_id=proposal_id,
        related_version_no=related_version_no,
    )
    handoff = _post_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}/execution-handoffs",
        expected_status=200,
        json_body={
            "actor_id": "ops_001",
            "execution_provider": "lotus-manage",
            "expected_state": "EXECUTION_READY",
            "related_version_no": related_version_no,
            "external_request_id": f"oms_req_{uuid.uuid4().hex[:10]}",
            "notes": {"channel": "OMS", "priority": "STANDARD"},
        },
        headers={"Idempotency-Key": f"live-handoff-{uuid.uuid4().hex}"},
    )
    _assert(
        handoff["handoff_status"] == "REQUESTED",
        f"{proposal_id}: unexpected handoff status {handoff['handoff_status']}",
    )

    requested_status = _get_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}/execution-status",
        expected_status=200,
    )
    _assert(
        requested_status["handoff_status"] == "REQUESTED",
        (
            f"{proposal_id}: unexpected requested execution status "
            f"{requested_status['handoff_status']}"
        ),
    )

    accepted_status = _post_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}/execution-updates",
        expected_status=200,
        json_body={
            "update_id": f"exec_accept_{uuid.uuid4().hex[:10]}",
            "actor_id": "lotus-manage",
            "execution_request_id": handoff["execution_request_id"],
            "execution_provider": "lotus-manage",
            "update_status": "ACCEPTED",
            "related_version_no": related_version_no,
            "occurred_at": _utc_iso_after(seconds=1),
            "details": {"desk": "SG"},
        },
    )
    _assert(
        accepted_status["handoff_status"] == "ACCEPTED",
        f"{proposal_id}: unexpected accepted execution status {accepted_status['handoff_status']}",
    )

    executed_status = _post_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}/execution-updates",
        expected_status=200,
        json_body={
            "update_id": f"exec_done_{uuid.uuid4().hex[:10]}",
            "actor_id": "lotus-manage",
            "execution_request_id": handoff["execution_request_id"],
            "execution_provider": "lotus-manage",
            "update_status": "EXECUTED",
            "related_version_no": related_version_no,
            "external_execution_id": f"oms_fill_{uuid.uuid4().hex[:10]}",
            "occurred_at": _utc_iso_after(seconds=2),
            "details": {"filled_quantity": "100"},
        },
    )
    _assert(
        executed_status["handoff_status"] == "EXECUTED",
        f"{proposal_id}: unexpected terminal execution status {executed_status['handoff_status']}",
    )

    capabilities = _get_json(
        client,
        url=f"{advise_base_url}/platform/capabilities",
        expected_status=200,
    )
    report_feature = _feature_by_key(capabilities, "advisory.proposals.reporting")
    report_response = client.post(
        f"{advise_base_url}/advisory/proposals/{proposal_id}/report-requests",
        json={
            "report_type": "CLIENT_PROPOSAL_SUMMARY",
            "requested_by": "advisor_1",
            "related_version_no": related_version_no,
            "include_execution_summary": True,
        },
    )
    if report_feature["operational_ready"]:
        _assert(
            report_response.status_code == 200,
            (
                f"{proposal_id}: expected live report request success, got "
                f"{report_response.status_code} body={report_response.text}"
            ),
        )
        report_body = cast(dict[str, Any], report_response.json())
        _assert(
            report_body["report_service"] == "lotus-report",
            f"{proposal_id}: unexpected report service {report_body['report_service']}",
        )
        _assert(
            report_body["status"] == "READY",
            f"{proposal_id}: unexpected report status {report_body['status']}",
        )
        _assert_persisted_read_surfaces(
            client,
            advise_base_url=advise_base_url,
            proposal_id=proposal_id,
            expected_portfolio_id=scenario.portfolio_id,
            created_by_filter="live-parity-validator",
            current_version_no=related_version_no,
            expected_state="EXECUTED",
            expected_report_status=report_body["status"],
        )
        return (
            scenario.portfolio_id,
            related_version_no,
            "EXECUTED",
            handoff["handoff_status"],
            report_body["status"],
        )

    _assert(
        report_response.status_code == 503,
        (
            f"{proposal_id}: expected lotus-report degraded 503, got "
            f"{report_response.status_code} body={report_response.text}"
        ),
    )
    detail = cast(dict[str, Any], report_response.json()).get("detail")
    _assert(
        detail == "LOTUS_REPORT_REQUEST_UNAVAILABLE",
        f"{proposal_id}: unexpected degraded report detail {detail}",
    )
    _assert_persisted_read_surfaces(
        client,
        advise_base_url=advise_base_url,
        proposal_id=proposal_id,
        expected_portfolio_id=scenario.portfolio_id,
        created_by_filter="live-parity-validator",
        current_version_no=related_version_no,
        expected_state="EXECUTED",
        expected_report_status="UNAVAILABLE",
    )
    return (
        scenario.portfolio_id,
        related_version_no,
        "EXECUTED",
        handoff["handoff_status"],
        "UNAVAILABLE",
    )


def _assert_async_lifecycle_read_surfaces(
    client: httpx.Client,
    *,
    advise_base_url: str,
    scenario: PortfolioParityScenario,
) -> tuple[str, int, str]:
    async_created = _submit_async_create(
        client,
        advise_base_url=advise_base_url,
        scenario=scenario,
        created_by="live-parity-validator-async-lifecycle",
    )
    async_create_result = _wait_for_async_success(
        client,
        advise_base_url=advise_base_url,
        operation_id=str(async_created["operation_id"]),
        expected_type="CREATE_PROPOSAL",
    )
    _assert_async_operation_surfaces(
        client,
        advise_base_url=advise_base_url,
        accepted_body=async_created,
        expected_type="CREATE_PROPOSAL",
        result_body=async_create_result,
    )
    async_proposal_id = str(async_create_result["proposal"]["proposal_id"])
    async_portfolio_id = str(async_create_result["proposal"]["portfolio_id"])
    async_version_no = int(async_create_result["version"]["version_no"])

    async_version_created = _submit_async_version(
        client,
        advise_base_url=advise_base_url,
        proposal_id=async_proposal_id,
        scenario=scenario,
        created_by="live-parity-validator-async-lifecycle-version",
        expected_current_version_no=async_version_no,
    )
    async_version_result = _wait_for_async_success(
        client,
        advise_base_url=advise_base_url,
        operation_id=str(async_version_created["operation_id"]),
        expected_type="CREATE_PROPOSAL_VERSION",
    )
    _assert_async_operation_surfaces(
        client,
        advise_base_url=advise_base_url,
        accepted_body=async_version_created,
        expected_type="CREATE_PROPOSAL_VERSION",
        result_body=async_version_result,
    )
    current_version_no = int(async_version_result["proposal"]["current_version_no"])
    _assert(
        current_version_no == async_version_no + 1,
        f"{async_proposal_id}: async lifecycle version did not increment current_version_no",
    )
    _promote_to_execution_ready(
        client,
        advise_base_url=advise_base_url,
        proposal_id=async_proposal_id,
        related_version_no=current_version_no,
    )
    handoff = _post_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{async_proposal_id}/execution-handoffs",
        expected_status=200,
        json_body={
            "actor_id": "ops_async_001",
            "execution_provider": "lotus-manage",
            "expected_state": "EXECUTION_READY",
            "related_version_no": current_version_no,
            "external_request_id": f"oms_async_req_{uuid.uuid4().hex[:10]}",
            "notes": {"channel": "OMS", "priority": "STANDARD"},
        },
        headers={"Idempotency-Key": f"live-async-lifecycle-handoff-{uuid.uuid4().hex}"},
    )
    _assert(
        handoff["handoff_status"] == "REQUESTED",
        f"{async_proposal_id}: async lifecycle handoff did not start in REQUESTED",
    )
    executed = _post_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{async_proposal_id}/execution-updates",
        expected_status=200,
        json_body={
            "update_id": f"async_exec_done_{uuid.uuid4().hex[:10]}",
            "actor_id": "lotus-manage",
            "execution_request_id": handoff["execution_request_id"],
            "execution_provider": "lotus-manage",
            "update_status": "EXECUTED",
            "related_version_no": current_version_no,
            "external_execution_id": f"oms_async_fill_{uuid.uuid4().hex[:10]}",
            "occurred_at": _utc_iso_after(seconds=2),
            "details": {"filled_quantity": "100"},
        },
    )
    _assert(
        executed["handoff_status"] == "EXECUTED",
        f"{async_proposal_id}: async lifecycle execution did not reach EXECUTED",
    )
    capabilities = _get_json(
        client,
        url=f"{advise_base_url}/platform/capabilities",
        expected_status=200,
    )
    report_feature = _feature_by_key(capabilities, "advisory.proposals.reporting")
    report_response = client.post(
        f"{advise_base_url}/advisory/proposals/{async_proposal_id}/report-requests",
        json={
            "report_type": "CLIENT_PROPOSAL_SUMMARY",
            "requested_by": "advisor_async_1",
            "related_version_no": current_version_no,
            "include_execution_summary": True,
        },
    )
    if report_feature["operational_ready"]:
        _assert(
            report_response.status_code == 200,
            (
                f"{async_proposal_id}: expected lotus-report ready path for async lifecycle, "
                f"got {report_response.status_code} body={report_response.text}"
            ),
        )
    else:
        _assert(
            report_response.status_code == 503,
            (
                f"{async_proposal_id}: expected lotus-report degraded 503 for async lifecycle, "
                f"got {report_response.status_code} body={report_response.text}"
            ),
        )
    _assert_persisted_read_surfaces(
        client,
        advise_base_url=advise_base_url,
        proposal_id=async_proposal_id,
        expected_portfolio_id=async_portfolio_id,
        created_by_filter="live-parity-validator-async-lifecycle",
        current_version_no=current_version_no,
        expected_state="EXECUTED",
        expected_report_status="READY" if report_feature["operational_ready"] else "UNAVAILABLE",
    )
    return async_portfolio_id, current_version_no, "EXECUTED"


def _assert_new_version_requires_fresh_approvals(
    client: httpx.Client,
    *,
    advise_base_url: str,
    scenario: PortfolioParityScenario,
) -> None:
    created = _create_stateful_proposal(
        client,
        advise_base_url=advise_base_url,
        scenario=scenario,
        created_by="live-parity-validator-approval-reset",
    )
    proposal_id = str(created["proposal"]["proposal_id"])
    _promote_to_execution_ready(
        client,
        advise_base_url=advise_base_url,
        proposal_id=proposal_id,
        related_version_no=int(created["version"]["version_no"]),
    )

    version_created = _create_stateful_version(
        client,
        advise_base_url=advise_base_url,
        proposal_id=proposal_id,
        scenario=scenario,
        created_by="live-parity-validator-approval-reset-version",
        expected_current_version_no=1,
    )
    proposal = cast(dict[str, Any], version_created["proposal"])
    _assert(
        int(proposal["current_version_no"]) == 2 and proposal["current_state"] == "DRAFT",
        f"{proposal_id}: new version did not reset lifecycle state after prior approvals",
    )

    handoff_response = client.post(
        f"{advise_base_url}/advisory/proposals/{proposal_id}/execution-handoffs",
        json={
            "actor_id": "ops_reset_001",
            "execution_provider": "lotus-manage",
            "expected_state": "EXECUTION_READY",
            "related_version_no": 2,
            "external_request_id": f"oms_req_reset_{uuid.uuid4().hex[:10]}",
            "notes": {"channel": "OMS"},
        },
    )
    _assert(
        handoff_response.status_code == 409,
        (
            f"{proposal_id}: expected stale-approval handoff conflict, got "
            f"{handoff_response.status_code} body={handoff_response.text}"
        ),
    )
    detail = cast(dict[str, Any], handoff_response.json()).get("detail", "")
    _assert(
        "STATE_CONFLICT" in str(detail) and "expected_state mismatch" in str(detail),
        f"{proposal_id}: stale-approval conflict detail unexpected {detail}",
    )


def _assert_workspace_flow(
    client: httpx.Client,
    *,
    advise_base_url: str,
    scenario: PortfolioParityScenario,
) -> None:
    create_body = _post_json(
        client,
        url=f"{advise_base_url}/advisory/workspaces",
        expected_status=201,
        json_body={
            "workspace_name": f"Live parity {scenario.portfolio_id}",
            "created_by": "live-parity-validator",
            "input_mode": "stateful",
            "stateful_input": {
                "portfolio_id": scenario.portfolio_id,
                "as_of": scenario.as_of_date,
            },
        },
    )
    workspace = create_body["workspace"]
    workspace_id = str(workspace["workspace_id"])
    _assert(
        workspace["resolved_context"]["portfolio_id"] == scenario.portfolio_id,
        f"{scenario.portfolio_id}: workspace resolved wrong portfolio context",
    )

    evaluated = _post_json(
        client,
        url=f"{advise_base_url}/advisory/workspaces/{workspace_id}/evaluate",
        expected_status=200,
        json_body={},
    )
    latest_result = evaluated.get("latest_proposal_result")
    _assert(
        isinstance(latest_result, dict),
        f"{scenario.portfolio_id}: workspace evaluate missing proposal result",
    )
    latest_result_dict = cast(dict[str, Any], latest_result)
    _assert_authority_posture(scenario=scenario, proposal_body=latest_result_dict)

    saved = _post_json(
        client,
        url=f"{advise_base_url}/advisory/workspaces/{workspace_id}/save",
        expected_status=200,
        json_body={"saved_by": "live-parity-validator", "version_label": "live-parity-baseline"},
    )
    saved_version = saved["saved_version"]
    workspace_version_id = str(saved_version["workspace_version_id"])
    saved_risk_lens = saved_version["replay_evidence"].get("risk_lens")
    _assert(
        isinstance(saved_risk_lens, dict) and saved_risk_lens.get("source_service") == "lotus-risk",
        f"{scenario.portfolio_id}: workspace saved replay evidence missing lotus-risk lens",
    )

    handoff = _post_json(
        client,
        url=f"{advise_base_url}/advisory/workspaces/{workspace_id}/handoff",
        expected_status=200,
        json_body={"handoff_by": "live-parity-validator"},
        headers={"Idempotency-Key": f"live-workspace-handoff-{uuid.uuid4().hex}"},
    )
    _assert(
        handoff["handoff_action"] == "CREATED_PROPOSAL",
        f"{scenario.portfolio_id}: unexpected workspace handoff action {handoff['handoff_action']}",
    )
    version = handoff["proposal"]["version"]
    proposal = handoff["proposal"]["proposal"]
    proposal_result = version["proposal_result"]
    _assert_authority_posture(scenario=scenario, proposal_body=proposal_result)

    workspace_replay = _request_json(
        client,
        method="GET",
        url=(
            f"{advise_base_url}/advisory/workspaces/{workspace_id}/saved-versions/"
            f"{workspace_version_id}/replay-evidence"
        ),
        expected_status=200,
    )
    proposal_replay = _request_json(
        client,
        method="GET",
        url=(
            f"{advise_base_url}/advisory/proposals/{proposal['proposal_id']}/versions/"
            f"{version['version_no']}/replay-evidence"
        ),
        expected_status=200,
    )
    _assert(
        workspace_replay["evidence"]["risk_lens"]["source_service"] == "lotus-risk",
        f"{scenario.portfolio_id}: workspace replay evidence missing lotus-risk source",
    )
    _assert(
        proposal_replay["evidence"]["risk_lens"]["source_service"] == "lotus-risk",
        f"{scenario.portfolio_id}: proposal replay evidence missing lotus-risk source",
    )
    _assert(
        workspace_replay["subject"]["proposal_id"] == proposal["proposal_id"],
        f"{scenario.portfolio_id}: workspace replay subject missing proposal linkage",
    )
    _assert(
        proposal_replay["continuity"]["workspace_version_id"] == workspace_version_id,
        f"{scenario.portfolio_id}: proposal replay continuity missing workspace version linkage",
    )
    _assert(
        workspace_replay["hashes"]["evaluation_request_hash"]
        == proposal_replay["hashes"]["evaluation_request_hash"],
        f"{scenario.portfolio_id}: workspace/proposal replay hashes diverged after handoff",
    )


def _assert_persisted_read_surfaces(
    client: httpx.Client,
    *,
    advise_base_url: str,
    proposal_id: str,
    expected_portfolio_id: str,
    created_by_filter: str | None,
    current_version_no: int,
    expected_state: str,
    expected_report_status: str,
) -> None:
    list_query = (
        f"{advise_base_url}/advisory/proposals"
        f"?portfolio_id={expected_portfolio_id}&limit=100"
    )
    if created_by_filter:
        list_query += f"&created_by={created_by_filter}"
    listed = _get_json(
        client,
        url=list_query,
        expected_status=200,
    )
    items = cast(list[dict[str, Any]], listed["items"])
    list_item = next(
        (item for item in items if str(item["proposal_id"]) == proposal_id),
        None,
    )
    _assert(
        isinstance(list_item, dict),
        f"{proposal_id}: proposal missing from list response for {expected_portfolio_id}",
    )
    list_item_dict = cast(dict[str, Any], list_item)

    detail = _get_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}?include_evidence=false",
        expected_status=200,
    )
    version = _get_json(
        client,
        url=(
            f"{advise_base_url}/advisory/proposals/{proposal_id}/versions/"
            f"{current_version_no}?include_evidence=false"
        ),
        expected_status=200,
    )
    timeline = _get_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}/workflow-events",
        expected_status=200,
    )
    lineage = _get_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}/lineage",
        expected_status=200,
    )
    approvals = _get_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}/approvals",
        expected_status=200,
    )
    delivery_summary = _get_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}/delivery-summary",
        expected_status=200,
    )
    delivery_history = _get_json(
        client,
        url=f"{advise_base_url}/advisory/proposals/{proposal_id}/delivery-events",
        expected_status=200,
    )

    _assert(
        str(list_item_dict["proposal_id"]) == str(detail["proposal"]["proposal_id"]) == proposal_id,
        f"{proposal_id}: list/detail proposal ids diverged",
    )
    _assert(
        str(detail["proposal"]["portfolio_id"]) == expected_portfolio_id,
        (
            f"{proposal_id}: detail endpoint returned wrong portfolio "
            f"{detail['proposal']['portfolio_id']}"
        ),
    )
    _assert(
        int(list_item_dict["current_version_no"])
        == int(detail["proposal"]["current_version_no"])
        == int(lineage["latest_version_no"])
        == current_version_no,
        f"{proposal_id}: current version diverged across list/detail/lineage",
    )
    _assert(
        str(list_item_dict["current_state"])
        == str(detail["proposal"]["current_state"])
        == str(timeline["current_state"])
        == str(delivery_summary["proposal"]["current_state"])
        == expected_state,
        f"{proposal_id}: current state diverged across read surfaces",
    )
    _assert(
        int(detail["current_version"]["version_no"])
        == int(version["version_no"])
        == current_version_no,
        f"{proposal_id}: detail/version endpoints diverged on current version",
    )
    _assert(
        str(version["proposal_id"]) == proposal_id,
        f"{proposal_id}: version endpoint returned wrong proposal id",
    )
    _assert(
        int(lineage["version_count"]) == current_version_no,
        f"{proposal_id}: lineage version count did not match latest version",
    )
    lineage_versions = cast(list[dict[str, Any]], lineage["versions"])
    _assert(
        [int(item["version_no"]) for item in lineage_versions]
        == list(range(1, current_version_no + 1)),
        f"{proposal_id}: lineage version numbers were not contiguous and ordered",
    )
    _assert(
        bool(lineage["lineage_complete"]) is True,
        f"{proposal_id}: lineage unexpectedly incomplete",
    )
    _assert(
        list(lineage["missing_version_numbers"]) == [],
        f"{proposal_id}: lineage unexpectedly reported missing versions",
    )
    timeline_events = cast(list[dict[str, Any]], timeline["events"])
    delivery_events = cast(list[dict[str, Any]], delivery_history["events"])
    _assert(
        int(timeline["event_count"]) == len(timeline_events),
        f"{proposal_id}: timeline event_count mismatch",
    )
    _assert(
        int(delivery_history["event_count"]) == len(delivery_events),
        f"{proposal_id}: delivery history event_count mismatch",
    )
    _assert(
        len(delivery_events) > 0 and len(timeline_events) >= len(delivery_events),
        f"{proposal_id}: delivery history unexpectedly empty or larger than timeline",
    )
    created_event = next(
        (event for event in timeline_events if event["event_type"] == "CREATED"),
        None,
    )
    _assert(
        isinstance(created_event, dict) and created_event["related_version_no"] == 1,
        f"{proposal_id}: missing version-1 CREATED event in workflow timeline",
    )
    if current_version_no > 1:
        new_version_events = [
            event for event in timeline_events if event["event_type"] == "NEW_VERSION_CREATED"
        ]
        _assert(
            len(new_version_events) == current_version_no - 1
            and {
                int(event["related_version_no"])
                for event in cast(list[dict[str, Any]], new_version_events)
            }
            == set(range(2, current_version_no + 1)),
            f"{proposal_id}: workflow timeline lost version-creation events",
        )
    _assert(
        all(
            event["event_type"]
            in {
                "EXECUTION_REQUESTED",
                "EXECUTION_ACCEPTED",
                "EXECUTION_PARTIALLY_EXECUTED",
                "EXECUTION_REJECTED",
                "EXECUTION_CANCELLED",
                "EXECUTION_EXPIRED",
                "EXECUTED",
                "REPORT_REQUESTED",
            }
            for event in delivery_events
        ),
        f"{proposal_id}: delivery history contained non-delivery events",
    )
    _assert(
        all(int(event["related_version_no"]) == current_version_no for event in delivery_events),
        f"{proposal_id}: delivery history leaked non-current version events",
    )
    _assert(
        int(approvals["approval_count"]) >= 2,
        f"{proposal_id}: approvals endpoint missing lifecycle approval records",
    )
    approval_rows = cast(list[dict[str, Any]], approvals["approvals"])
    _assert(
        all(
            int(approval["related_version_no"]) == current_version_no
            for approval in approval_rows
        ),
        f"{proposal_id}: approvals endpoint leaked non-current version approvals",
    )
    execution = cast(dict[str, Any], delivery_summary["execution"])
    _assert(
        execution["handoff_status"] == "EXECUTED",
        f"{proposal_id}: delivery summary execution did not reach EXECUTED",
    )
    _assert(
        execution["related_version_no"] == current_version_no,
        f"{proposal_id}: execution summary was not anchored to latest version",
    )
    _assert(
        str(cast(dict[str, Any], delivery_history["latest_event"])["event_type"])
        == (
            "REPORT_REQUESTED"
            if expected_report_status == "READY"
            else str(execution["latest_event_type"])
        ),
        f"{proposal_id}: delivery latest event did not match delivery posture",
    )
    reporting = delivery_summary.get("reporting")
    if expected_report_status == "READY":
        reporting_dict = cast(dict[str, Any], reporting)
        _assert(
            isinstance(reporting, dict) and reporting_dict["status"] == "READY",
            f"{proposal_id}: delivery summary missing ready reporting posture",
        )
        _assert(
            reporting_dict["related_version_no"] == current_version_no,
            f"{proposal_id}: report summary was not anchored to latest version",
        )
    else:
        _assert(
            reporting is None,
            f"{proposal_id}: delivery summary unexpectedly contained reporting posture",
        )
    if current_version_no > 1:
        first_version_replay = _get_json(
            client,
            url=(
                f"{advise_base_url}/advisory/proposals/{proposal_id}/versions/1/replay-evidence"
            ),
            expected_status=200,
        )
        current_version_replay = _get_json(
            client,
            url=(
                f"{advise_base_url}/advisory/proposals/{proposal_id}/versions/"
                f"{current_version_no}/replay-evidence"
            ),
            expected_status=200,
        )
        _assert(
            first_version_replay["subject"]["proposal_version_no"] == 1,
            f"{proposal_id}: version-1 replay subject lost immutable version identity",
        )
        _assert(
            current_version_replay["subject"]["proposal_version_no"] == current_version_no,
            f"{proposal_id}: current-version replay subject lost version identity",
        )


def validate_live_cross_service_parity(
    *,
    advise_base_url: str | None = None,
    core_query_base_url: str | None = None,
    risk_base_url: str | None = None,
    candidate_portfolios: tuple[str, ...] | None = None,
) -> LiveParityResult:
    advise_base_url = (
        advise_base_url or os.getenv("LOTUS_ADVISE_BASE_URL") or _DEFAULT_ADVISE_BASE_URL
    ).rstrip("/")
    core_query_base_url = (
        core_query_base_url
        or os.getenv("LOTUS_CORE_QUERY_BASE_URL")
        or _DEFAULT_CORE_QUERY_BASE_URL
    ).rstrip("/")
    risk_base_url = (
        risk_base_url or os.getenv("LOTUS_RISK_BASE_URL") or _DEFAULT_RISK_BASE_URL
    ).rstrip("/")
    candidates = candidate_portfolios or tuple(
        value.strip()
        for value in os.getenv(
            "LOTUS_PARITY_PORTFOLIOS",
            ",".join(_DEFAULT_PORTFOLIO_CANDIDATES),
        ).split(",")
        if value.strip()
    )

    with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
        complete, degraded = _select_scenarios(
            client,
            advise_base_url=advise_base_url,
            core_query_base_url=core_query_base_url,
            candidates=candidates,
        )

        for scenario in (complete, degraded):
            proposal_body = _simulate_stateful_noop(
                client,
                advise_base_url=advise_base_url,
                portfolio_id=scenario.portfolio_id,
                as_of_date=scenario.as_of_date,
            )
            direct_allocation = _query_live_allocation(
                client,
                core_query_base_url=core_query_base_url,
                portfolio_id=scenario.portfolio_id,
                as_of_date=scenario.as_of_date,
                reporting_currency=scenario.reporting_currency,
            )
            _assert_allocation_parity(
                scenario=scenario,
                direct_allocation=direct_allocation,
                proposal_body=proposal_body,
            )
            if scenario.risk_available:
                _assert_authority_posture(
                    scenario=scenario,
                    proposal_body=proposal_body,
                )
                direct_risk = _query_direct_concentration(
                    client,
                    risk_base_url=risk_base_url,
                    portfolio_id=scenario.portfolio_id,
                    as_of_date=scenario.as_of_date,
                    reporting_currency=scenario.reporting_currency,
                )
                _assert_risk_parity(
                    scenario=scenario,
                    direct_risk=direct_risk,
                    proposal_body=proposal_body,
                )
            else:
                authority_resolution = proposal_body.get("explanation", {}).get(
                    "authority_resolution"
                )
                _assert(
                    isinstance(authority_resolution, dict)
                    and authority_resolution.get("risk_authority") == "unavailable"
                    and authority_resolution.get("degraded") is True,
                    (
                        f"{scenario.portfolio_id}: expected degraded risk-unavailable posture, got "
                        f"{authority_resolution}"
                    ),
                )
                _assert(
                    "risk_lens" not in proposal_body.get("explanation", {}),
                    (
                        f"{scenario.portfolio_id}: degraded risk-unavailable scenario "
                        "exposed risk_lens"
                    ),
                )

        cold_ms, warm_ms = _measure_warm_cache(
            client,
            advise_base_url=advise_base_url,
            scenario=complete,
        )
        (
            lifecycle_portfolio,
            lifecycle_latest_version_no,
            lifecycle_current_state,
            handoff_status,
            report_status,
        ) = _assert_lifecycle_and_delivery_flow(
            client,
            advise_base_url=advise_base_url,
            scenario=complete,
        )
        (
        async_lifecycle_portfolio,
        async_lifecycle_latest_version_no,
        async_lifecycle_current_state,
    ) = _assert_async_lifecycle_read_surfaces(
        client,
        advise_base_url=advise_base_url,
        scenario=complete,
    )
        _assert_new_version_requires_fresh_approvals(
            client,
            advise_base_url=advise_base_url,
            scenario=complete,
        )
        _assert_mixed_approval_routes_remain_version_scoped(
            client,
            advise_base_url=advise_base_url,
            scenario=complete,
        )
        _assert_workspace_flow(
            client,
            advise_base_url=advise_base_url,
            scenario=complete,
        )

    return LiveParityResult(
        complete_issuer_portfolio=complete.portfolio_id,
        degraded_issuer_portfolio=degraded.portfolio_id,
        degraded_issuer_coverage_status=degraded.issuer_coverage_status,
        cold_duration_ms=cold_ms,
        warm_duration_ms=warm_ms,
        workspace_handoff_portfolio=complete.portfolio_id,
        lifecycle_portfolio=lifecycle_portfolio,
        lifecycle_latest_version_no=lifecycle_latest_version_no,
        lifecycle_current_state=lifecycle_current_state,
        async_lifecycle_portfolio=async_lifecycle_portfolio,
        async_lifecycle_latest_version_no=async_lifecycle_latest_version_no,
        async_lifecycle_current_state=async_lifecycle_current_state,
        execution_handoff_status=handoff_status,
        execution_terminal_status="EXECUTED",
        report_status=report_status,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate live cross-service allocation and risk parity across "
            "lotus-advise, lotus-core, and lotus-risk."
        )
    )
    parser.add_argument("--advise-base-url", default=None)
    parser.add_argument("--core-query-base-url", default=None)
    parser.add_argument("--risk-base-url", default=None)
    parser.add_argument(
        "--candidate-portfolio",
        action="append",
        dest="candidate_portfolios",
        help="Candidate seeded portfolio_id to probe for complete/partial issuer coverage.",
    )
    args = parser.parse_args()

    result = validate_live_cross_service_parity(
        advise_base_url=args.advise_base_url,
        core_query_base_url=args.core_query_base_url,
        risk_base_url=args.risk_base_url,
        candidate_portfolios=(
            tuple(args.candidate_portfolios) if args.candidate_portfolios else None
        ),
    )
    print(
        "Cross-service parity validation passed "
        f"(complete={result.complete_issuer_portfolio}, "
        f"degraded={result.degraded_issuer_portfolio}:"
        f"{result.degraded_issuer_coverage_status}, "
        f"cold_ms={result.cold_duration_ms:.2f}, "
        f"warm_ms={result.warm_duration_ms:.2f})"
    )


if __name__ == "__main__":
    main()
