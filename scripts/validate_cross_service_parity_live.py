from __future__ import annotations

import argparse
import os
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, cast

import httpx

_DEFAULT_ADVISE_BASE_URL = "http://127.0.0.1:8000"
_DEFAULT_CORE_QUERY_BASE_URL = "http://127.0.0.1:8201"
_DEFAULT_RISK_BASE_URL = "http://127.0.0.1:8130"
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


class LiveParityValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class PortfolioParityScenario:
    portfolio_id: str
    as_of_date: str
    reporting_currency: str
    issuer_coverage_status: str


@dataclass(frozen=True)
class LiveParityResult:
    complete_issuer_portfolio: str
    degraded_issuer_portfolio: str
    degraded_issuer_coverage_status: str
    cold_duration_ms: float
    warm_duration_ms: float


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise LiveParityValidationError(message)


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


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
        risk_lens = simulate.get("explanation", {}).get("risk_lens")
        _assert(
            isinstance(risk_lens, dict),
            (
                f"{portfolio_id}: proposal response did not expose risk_lens; "
                f"authority={simulate.get('explanation', {}).get('authority_resolution')}"
            ),
        )
        coverage_status = str(
            risk_lens["issuer_concentration"]["coverage_status"]
        )
        examined.append((portfolio_id, coverage_status))
        scenario = PortfolioParityScenario(
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            reporting_currency=reporting_currency,
            issuer_coverage_status=coverage_status,
        )
        if coverage_status == "complete" and complete is None:
            complete = scenario
        elif coverage_status in {"partial", "unavailable"} and degraded is None:
            degraded = scenario
        elif (
            coverage_status == "partial"
            and degraded is not None
            and degraded.issuer_coverage_status != "partial"
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
    _assert(
        warm_ms <= cold_ms * 1.25,
        (
            f"{scenario.portfolio_id}: warm cache regression detected "
            f"cold_ms={cold_ms:.2f} warm_ms={warm_ms:.2f}"
        ),
    )
    return cold_ms, warm_ms


def validate_live_cross_service_parity(
    *,
    advise_base_url: str | None = None,
    core_query_base_url: str | None = None,
    risk_base_url: str | None = None,
    candidate_portfolios: tuple[str, ...] | None = None,
) -> LiveParityResult:
    advise_base_url = (
        advise_base_url
        or os.getenv("LOTUS_ADVISE_BASE_URL")
        or _DEFAULT_ADVISE_BASE_URL
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
            direct_risk = _query_direct_concentration(
                client,
                risk_base_url=risk_base_url,
                portfolio_id=scenario.portfolio_id,
                as_of_date=scenario.as_of_date,
                reporting_currency=scenario.reporting_currency,
            )
            _assert_allocation_parity(
                scenario=scenario,
                direct_allocation=direct_allocation,
                proposal_body=proposal_body,
            )
            _assert_authority_posture(
                scenario=scenario,
                proposal_body=proposal_body,
            )
            _assert_risk_parity(
                scenario=scenario,
                direct_risk=direct_risk,
                proposal_body=proposal_body,
            )

        cold_ms, warm_ms = _measure_warm_cache(
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
