from __future__ import annotations

import os
import subprocess
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, cast

import httpx

_DEFAULT_ADVISE_BASE_URL = "http://advise.dev.lotus"
_DEFAULT_CORE_CONTROL_BASE_URL = "http://core-control.dev.lotus"
_DEFAULT_CORE_QUERY_BASE_URL = "http://core-query.dev.lotus"
_DEFAULT_RISK_BASE_URL = "http://risk.dev.lotus"


class LiveDegradedValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class DegradedRuntimeResult:
    risk_drill_portfolio: str
    risk_degraded_reason: str
    core_degraded_reason: str
    fallback_mode: str


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise LiveDegradedValidationError(message)


def _run_docker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args],
        check=True,
        capture_output=True,
        text=True,
    )


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
            f"{method} {url}: expected HTTP {expected_status}, got {response.status_code}, "
            f"body={response.text}"
        ),
    )
    payload = response.json()
    _assert(isinstance(payload, dict), f"{method} {url}: expected object payload")
    return dict(payload)


def _feature_by_key(capabilities: dict[str, Any], key: str) -> dict[str, Any]:
    features = capabilities.get("features")
    _assert(isinstance(features, list), "/platform/capabilities: features must be a list")
    feature_list = cast(list[Any], features)
    for feature in feature_list:
        if isinstance(feature, dict) and feature.get("key") == key:
            return feature
    raise LiveDegradedValidationError(f"/platform/capabilities: missing feature {key}")


def _dependency_by_key(capabilities: dict[str, Any], key: str) -> dict[str, Any]:
    readiness = capabilities.get("readiness") or {}
    dependencies = readiness.get("dependencies")
    _assert(
        isinstance(dependencies, list),
        "/platform/capabilities: readiness.dependencies must be a list",
    )
    dependency_list = cast(list[Any], dependencies)
    for dependency in dependency_list:
        if isinstance(dependency, dict) and dependency.get("dependency_key") == key:
            return dependency
    raise LiveDegradedValidationError(f"/platform/capabilities: missing dependency {key}")


def _resolve_container_name(*substrings: str) -> str:
    output = _run_docker("ps", "-a", "--format", "{{.Names}}").stdout
    names = [line.strip() for line in output.splitlines() if line.strip()]
    matches = [name for name in names if all(fragment in name for fragment in substrings)]
    _assert(
        len(matches) == 1,
        f"expected one container for {substrings}, found {matches or 'none'}",
    )
    return matches[0]


def _wait_for_http(
    url: str,
    *,
    expect_ready: bool,
    timeout_seconds: float = 60.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    with httpx.Client(timeout=5.0) as client:
        while time.monotonic() < deadline:
            try:
                response = client.get(url)
                if expect_ready and response.status_code == 200:
                    return
                if not expect_ready and response.status_code >= 500:
                    return
            except httpx.HTTPError:
                if not expect_ready:
                    return
            time.sleep(1.0)
    raise LiveDegradedValidationError(
        f"timeout waiting for {'ready' if expect_ready else 'unavailable'}: {url}"
    )


@contextmanager
def _temporarily_stopped(
    container_name: str,
    *,
    readiness_url: str | None = None,
) -> Iterator[None]:
    _run_docker("stop", container_name)
    if readiness_url:
        _wait_for_http(readiness_url, expect_ready=False)
    try:
        yield
    finally:
        _run_docker("start", container_name)
        if readiness_url:
            _wait_for_http(readiness_url, expect_ready=True)


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


def _risk_unavailable_drill(
    client: httpx.Client,
    *,
    advise_base_url: str,
    core_query_base_url: str,
    risk_base_url: str,
) -> tuple[str, str]:
    portfolio_id = "PB_SG_GLOBAL_BAL_001"
    as_of_date, _ = _resolve_latest_portfolio_context(
        client,
        core_query_base_url=core_query_base_url,
        portfolio_id=portfolio_id,
    )
    risk_container = _resolve_container_name("lotus-risk", "lotus-risk")

    with _temporarily_stopped(risk_container, readiness_url=f"{risk_base_url}/health/ready"):
        response = client.post(
            f"{advise_base_url}/advisory/proposals/simulate",
            json={
                "input_mode": "stateful",
                "stateful_input": {"portfolio_id": portfolio_id, "as_of": as_of_date},
            },
            headers={"Idempotency-Key": f"degraded-risk-{uuid.uuid4().hex}"},
        )
        _assert(
            response.status_code == 200,
            f"risk unavailable drill simulate failed: {response.status_code} {response.text}",
        )
        body = response.json()
        authority = body["explanation"]["authority_resolution"]
        _assert(
            authority["simulation_authority"] == "lotus_core",
            f"risk unavailable drill lost lotus-core simulation authority: {authority}",
        )
        _assert(
            authority["risk_authority"] == "unavailable" and authority["degraded"] is True,
            f"risk unavailable drill did not degrade cleanly: {authority}",
        )
        _assert(
            authority["degraded_reasons"] == ["LOTUS_RISK_ENRICHMENT_UNAVAILABLE"],
            f"risk unavailable drill returned unexpected degraded reasons: {authority}",
        )
        _assert(
            "risk_lens" not in body["explanation"],
            "risk unavailable drill unexpectedly exposed risk_lens",
        )

        capabilities = _request_json(
            client,
            method="GET",
            url=f"{advise_base_url}/platform/capabilities",
            expected_status=200,
        )
        risk_feature = _feature_by_key(capabilities, "advisory.proposals.risk_lens")
        simulation_feature = _feature_by_key(capabilities, "advisory.proposals.simulation")
        _assert(
            risk_feature["operational_ready"] is False
            and risk_feature["degraded_reason"] == "LOTUS_RISK_DEPENDENCY_UNAVAILABLE",
            f"risk unavailable drill capabilities did not mark risk degraded: {risk_feature}",
        )
        _assert(
            simulation_feature["operational_ready"] is True,
            (
                "risk unavailable drill unexpectedly degraded simulation feature: "
                f"{simulation_feature}"
            ),
        )
        return portfolio_id, str(risk_feature["degraded_reason"])


def _core_unavailable_drill(
    client: httpx.Client,
    *,
    advise_base_url: str,
    core_control_base_url: str,
    core_query_base_url: str,
) -> tuple[str, str]:
    control_container = _resolve_container_name("lotus-core", "query_control_plane_service")
    query_container = _resolve_container_name("lotus-core", "query_service")
    stateless_payload = {
        "portfolio_snapshot": {
            "portfolio_id": "pf_live_core_unavailable",
            "base_currency": "USD",
            "positions": [],
            "cash_balances": [{"currency": "USD", "amount": "1000"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
            "fx_rates": [],
        },
        "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [{"currency": "USD", "amount": "200"}],
        "proposed_trades": [{"side": "BUY", "instrument_id": "EQ_1", "quantity": "2"}],
    }

    with _temporarily_stopped(
        control_container,
        readiness_url=f"{core_control_base_url}/health/ready",
    ):
        with _temporarily_stopped(
            query_container,
            readiness_url=f"{core_query_base_url}/health/ready",
        ):
            response = client.post(
                f"{advise_base_url}/advisory/proposals/simulate",
                json=stateless_payload,
                headers={"Idempotency-Key": f"degraded-core-{uuid.uuid4().hex}"},
            )
            _assert(
                response.status_code in {502, 503},
                (
                    "core unavailable drill unexpectedly succeeded: "
                    f"{response.status_code} {response.text}"
                ),
            )
            body = response.json()
            detail = str(body["detail"])
            _assert(
                detail.startswith("LOTUS_CORE_SIMULATION_UNAVAILABLE"),
                f"core unavailable drill returned unexpected detail: {detail}",
            )

            capabilities = _request_json(
                client,
                method="GET",
                url=f"{advise_base_url}/platform/capabilities",
                expected_status=200,
            )
            simulation_feature = _feature_by_key(capabilities, "advisory.proposals.simulation")
            core_dependency = _dependency_by_key(capabilities, "lotus_core")
            _assert(
                simulation_feature["operational_ready"] is False
                and simulation_feature["degraded_reason"] == "LOTUS_CORE_DEPENDENCY_UNAVAILABLE",
                (
                    "core unavailable drill capabilities did not mark simulation degraded: "
                    f"{simulation_feature}"
                ),
            )
            _assert(
                simulation_feature["fallback_mode"] == "NONE",
                f"core unavailable drill unexpectedly exposed fallback mode: {simulation_feature}",
            )
            _assert(
                core_dependency["fallback_mode"] == "NONE",
                (
                    "core unavailable drill dependency unexpectedly exposed fallback mode: "
                    f"{core_dependency}"
                ),
            )
            return (
                str(simulation_feature["degraded_reason"]),
                str(simulation_feature["fallback_mode"]),
            )


def validate_live_degraded_runtime(
    *,
    advise_base_url: str | None = None,
    core_control_base_url: str | None = None,
    core_query_base_url: str | None = None,
    risk_base_url: str | None = None,
) -> DegradedRuntimeResult:
    advise_base_url = (
        advise_base_url or os.getenv("LOTUS_ADVISE_BASE_URL") or _DEFAULT_ADVISE_BASE_URL
    )
    core_control_base_url = (
        core_control_base_url
        or os.getenv("LOTUS_CORE_BASE_URL")
        or _DEFAULT_CORE_CONTROL_BASE_URL
    )
    core_query_base_url = (
        core_query_base_url
        or os.getenv("LOTUS_CORE_QUERY_BASE_URL")
        or _DEFAULT_CORE_QUERY_BASE_URL
    )
    risk_base_url = risk_base_url or os.getenv("LOTUS_RISK_BASE_URL") or _DEFAULT_RISK_BASE_URL

    with httpx.Client(timeout=15.0) as client:
        _wait_for_http(f"{advise_base_url}/health/ready", expect_ready=True)
        _wait_for_http(f"{core_control_base_url}/health/ready", expect_ready=True)
        _wait_for_http(f"{core_query_base_url}/health/ready", expect_ready=True)
        _wait_for_http(f"{risk_base_url}/health/ready", expect_ready=True)

        portfolio_id, risk_reason = _risk_unavailable_drill(
            client,
            advise_base_url=advise_base_url,
            core_query_base_url=core_query_base_url,
            risk_base_url=risk_base_url,
        )
        core_reason, fallback_mode = _core_unavailable_drill(
            client,
            advise_base_url=advise_base_url,
            core_control_base_url=core_control_base_url,
            core_query_base_url=core_query_base_url,
        )
        return DegradedRuntimeResult(
            risk_drill_portfolio=portfolio_id,
            risk_degraded_reason=risk_reason,
            core_degraded_reason=core_reason,
            fallback_mode=fallback_mode,
        )


if __name__ == "__main__":
    result = validate_live_degraded_runtime()
    print(
        "Live degraded runtime validation passed "
        f"(risk_portfolio={result.risk_drill_portfolio}, "
        f"risk_reason={result.risk_degraded_reason}, "
        f"core_reason={result.core_degraded_reason}, "
        f"fallback_mode={result.fallback_mode})"
    )
