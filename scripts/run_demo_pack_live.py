import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "docs" / "demo"


class DemoRunError(RuntimeError):
    pass


REQUIRED_FEATURE_KEYS = {
    "advisory.proposals.simulation",
    "advisory.proposals.lifecycle",
    "advisory.proposals.async_operations",
    "advisory.workspaces.stateful",
    "advisory.proposals.risk_lens",
    "advisory.proposals.reporting",
    "advisory.proposals.reviewed_narrative_evidence",
    "advisory.proposals.memo_evidence_pack",
    "advisory.policy_pack_catalog",
    "advisory.proposals.policy_evaluation",
    "advisory.advisor_cockpit",
    "advisory.advisory_copilot",
    "advisory.bank_demo_proof",
    "advisory.proposals.execution_handoff",
    "advise.observability.advisory_supportability",
}

REQUIRED_WORKFLOW_KEYS = {
    "advisory_proposal_simulation",
    "advisory_proposal_lifecycle",
    "advisory_workspace_stateful",
    "advisory_proposal_risk_lens",
    "advisory_proposal_reporting",
    "advisory_proposal_reviewed_narrative_evidence",
    "advisory_proposal_memo_evidence_pack",
    "advisory_policy_pack_catalog",
    "advisory_policy_evaluation",
    "advisor_cockpit_operating_workflow",
    "advisory_copilot_interaction",
    "advisory_bank_demo_proof",
    "advisory_proposal_execution_handoff",
}

PATH_PARAMETER_VALUES = {
    "action_item_id": "demo-action-id",
    "correlation_id": "demo-correlation-id",
    "evaluation_id": "demo-evaluation-id",
    "evidence_packet_id": "demo-evidence-packet-id",
    "idempotency_key": "demo-idempotency-key",
    "operation_id": "demo-operation-id",
    "policy_pack_id": "GLOBAL_PRIVATE_BANKING_BASELINE",
    "policy_version": "2026.05",
    "proposal_id": "demo-proposal-id",
    "proposal_version_id": "demo-proposal-version-id",
    "run_id": "demo-run-id",
    "version_id": "demo-version-id",
    "version_no": "1",
    "workspace_id": "demo-workspace-id",
    "workspace_version_id": "demo-workspace-version-id",
}

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _load_json(filename: str) -> dict[str, Any]:
    return json.loads((DEMO_DIR / filename).read_text(encoding="utf-8"))


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise DemoRunError(message)


def _run_scenario(
    client: httpx.Client,
    *,
    name: str,
    method: str,
    path: str,
    expected_http: int,
    payload_file: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload = _load_json(payload_file) if payload_file else None
    response = client.request(method, path, json=payload, headers=headers)
    _assert(
        response.status_code == expected_http,
        f"{name}: expected HTTP {expected_http}, got {response.status_code}, body={response.text}",
    )
    if response.content:
        return response.json()
    return {}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _openapi_operations(schema: dict[str, Any]) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for path, methods in sorted(schema.get("paths", {}).items()):
        for method, operation in sorted(methods.items()):
            if method.lower() not in HTTP_METHODS:
                continue
            request_body = operation.get("requestBody", {})
            operations.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "operationId": operation.get("operationId"),
                    "tags": operation.get("tags", []),
                    "requiresRequestBody": bool(request_body.get("required")),
                }
            )
    return operations


def _sample_path(path: str) -> str:
    sampled = path
    for name, value in PATH_PARAMETER_VALUES.items():
        sampled = sampled.replace("{" + name + "}", value)
    return sampled


def _route_safety_probe(client: httpx.Client, operation: dict[str, Any]) -> dict[str, Any]:
    method = operation["method"]
    path = _sample_path(operation["path"])
    record = {
        "method": method,
        "path": operation["path"],
        "sampledPath": path,
        "operationId": operation["operationId"],
        "status": "skipped",
        "httpStatus": None,
        "reason": None,
    }
    if "{" in path or "}" in path:
        record["reason"] = "missing_path_parameter_sample"
        return record
    if method not in {"GET", "POST"}:
        record["reason"] = "method_not_used_by_lotus_advise"
        return record
    if method == "POST" and not operation["requiresRequestBody"]:
        record["reason"] = "mutating_no_required_body_operation_not_probed"
        return record

    response = client.request(
        method,
        path,
        json={"__demo_certification_invalid_probe__": True} if method == "POST" else None,
        headers={"Idempotency-Key": f"demo-cert-route-probe-{uuid.uuid4().hex[:8]}"},
    )
    record["status"] = "probed"
    record["httpStatus"] = response.status_code
    _assert(
        response.status_code < 500 and response.status_code != 405,
        (
            f"{method} {operation['path']}: unsafe route probe response "
            f"{response.status_code}, body={response.text}"
        ),
    )
    return record


def _assert_capability_truth(capabilities: dict[str, Any]) -> dict[str, Any]:
    feature_records = {item.get("key"): item for item in capabilities.get("features", [])}
    workflow_records = {
        item.get("workflow_key"): item for item in capabilities.get("workflows", [])
    }

    missing_features = sorted(REQUIRED_FEATURE_KEYS - set(feature_records))
    missing_workflows = sorted(REQUIRED_WORKFLOW_KEYS - set(workflow_records))
    disabled_features = sorted(
        key
        for key in REQUIRED_FEATURE_KEYS
        if key in feature_records and not feature_records[key].get("enabled")
    )
    disabled_workflows = sorted(
        key
        for key in REQUIRED_WORKFLOW_KEYS
        if key in workflow_records and not workflow_records[key].get("enabled")
    )
    weak_features = sorted(
        key
        for key in REQUIRED_FEATURE_KEYS
        if key in feature_records and not _is_ready_or_truthfully_degraded(feature_records[key])
    )
    weak_workflows = sorted(
        key
        for key in REQUIRED_WORKFLOW_KEYS
        if key in workflow_records and not _is_ready_or_truthfully_degraded(workflow_records[key])
    )

    _assert(not missing_features, f"Missing required capability features: {missing_features}")
    _assert(not missing_workflows, f"Missing required capability workflows: {missing_workflows}")
    _assert(
        not disabled_features, f"Required capability features are disabled: {disabled_features}"
    )
    _assert(
        not disabled_workflows,
        f"Required capability workflows are disabled: {disabled_workflows}",
    )
    _assert(not weak_features, f"Required capability features are not ready: {weak_features}")
    _assert(not weak_workflows, f"Required capability workflows are not ready: {weak_workflows}")

    return {
        "requiredFeatureCount": len(REQUIRED_FEATURE_KEYS),
        "requiredWorkflowCount": len(REQUIRED_WORKFLOW_KEYS),
        "degradedRequiredFeatures": sorted(
            key
            for key in REQUIRED_FEATURE_KEYS
            if key in feature_records and not feature_records[key].get("operational_ready")
        ),
        "degradedRequiredWorkflows": sorted(
            key
            for key in REQUIRED_WORKFLOW_KEYS
            if key in workflow_records and not workflow_records[key].get("operational_ready")
        ),
        "supportability": capabilities.get("supportability", {}),
        "readiness": capabilities.get("readiness", {}),
    }


def _is_ready_or_truthfully_degraded(record: dict[str, Any]) -> bool:
    if record.get("operational_ready"):
        return True
    return bool(record.get("dependency_keys")) and bool(record.get("degraded_reason"))


def _new_evidence(base_url: str) -> dict[str, Any]:
    return {
        "generatedAt": _utc_now(),
        "baseUrl": base_url,
        "status": "failed",
        "openapi": {},
        "capabilities": {},
        "scenarios": [],
        "routeSafetyProbes": [],
        "domainAssertions": [],
    }


def _certify_foundation(client: httpx.Client, evidence: dict[str, Any]) -> None:
    health = _run_scenario(
        client,
        name="health_ready",
        method="GET",
        path="/health/ready",
        expected_http=200,
    )
    _assert(health.get("status") == "ready", "health_ready: service is not ready")
    evidence["domainAssertions"].append({"name": "health_ready", "status": health.get("status")})

    openapi_schema = _run_scenario(
        client,
        name="openapi",
        method="GET",
        path="/openapi.json",
        expected_http=200,
    )
    operations = _openapi_operations(openapi_schema)
    evidence["openapi"] = {
        "pathCount": len(openapi_schema.get("paths", {})),
        "operationCount": len(operations),
        "operations": operations,
    }
    _assert(len(operations) >= 80, "openapi: expected at least 80 documented operations")

    capabilities = _run_scenario(
        client,
        name="platform_capabilities",
        method="GET",
        path="/platform/capabilities",
        expected_http=200,
    )
    evidence["capabilities"] = _assert_capability_truth(capabilities)

    route_probe_records = [_route_safety_probe(client, operation) for operation in operations]
    evidence["routeSafetyProbes"] = route_probe_records
    _assert(
        any(item["status"] == "probed" for item in route_probe_records),
        "route-safety: no OpenAPI operations were probed",
    )


def _certify_simulation_scenarios(client: httpx.Client, evidence: dict[str, Any]) -> None:
    advisory_expected = {
        "10_advisory_proposal_simulate.json": "READY",
        "11_advisory_auto_funding_single_ccy.json": "READY",
        "12_advisory_partial_funding.json": "READY",
        "13_advisory_missing_fx_blocked.json": "BLOCKED",
        "14_advisory_drift_asset_class.json": "READY",
        "15_advisory_drift_instrument.json": "READY",
        "16_advisory_suitability_resolved_single_position.json": "READY",
        "17_advisory_suitability_new_issuer_breach.json": "READY",
        "18_advisory_suitability_sell_only_violation.json": "BLOCKED",
    }
    for file_name, expected in advisory_expected.items():
        body = _run_scenario(
            client,
            name=file_name,
            method="POST",
            path="/advisory/proposals/simulate",
            expected_http=200,
            payload_file=file_name,
            headers={"Idempotency-Key": f"live-{file_name}"},
        )
        _assert(
            body.get("status") == expected,
            f"{file_name}: unexpected status {body.get('status')}",
        )
        evidence["scenarios"].append(
            {
                "name": file_name,
                "path": "/advisory/proposals/simulate",
                "expectedStatus": expected,
                "observedStatus": body.get("status"),
            }
        )


def _certify_artifact_scenario(client: httpx.Client, evidence: dict[str, Any]) -> None:
    artifact = _run_scenario(
        client,
        name="19_advisory_proposal_artifact.json",
        method="POST",
        path="/advisory/proposals/artifact",
        expected_http=200,
        payload_file="19_advisory_proposal_artifact.json",
        headers={"Idempotency-Key": "live-demo-artifact-19"},
    )
    _assert(artifact.get("status") == "READY", "19_advisory_proposal_artifact.json: not READY")
    artifact_hash = artifact.get("evidence_bundle", {}).get("hashes", {}).get("artifact_hash", "")
    _assert(
        artifact_hash.startswith("sha256:"),
        "19_advisory_proposal_artifact.json: missing artifact hash",
    )
    evidence["scenarios"].append(
        {
            "name": "19_advisory_proposal_artifact.json",
            "path": "/advisory/proposals/artifact",
            "expectedStatus": "READY",
            "observedStatus": artifact.get("status"),
            "recommendedNextStep": artifact.get("summary", {}).get("recommended_next_step"),
            "artifactHashPrefix": artifact_hash[:7],
        }
    )


def _record_state_scenario(
    evidence: dict[str, Any],
    *,
    name: str,
    path: str,
    expected_state: str,
    observed_state: str,
) -> None:
    evidence["scenarios"].append(
        {
            "name": name,
            "path": path,
            "expectedState": expected_state,
            "observedState": observed_state,
        }
    )


def _certify_lifecycle_scenarios(client: httpx.Client, evidence: dict[str, Any]) -> None:
    create = _run_scenario(
        client,
        name="20_advisory_proposal_persist_create.json",
        method="POST",
        path="/advisory/proposals",
        expected_http=200,
        payload_file="20_advisory_proposal_persist_create.json",
        headers={"Idempotency-Key": f"live-demo-lifecycle-20-{uuid.uuid4().hex[:8]}"},
    )
    proposal_id = create["proposal"]["proposal_id"]
    _assert(create["proposal"]["current_state"] == "DRAFT", "20: unexpected lifecycle state")
    _record_state_scenario(
        evidence,
        name="20_advisory_proposal_persist_create.json",
        path="/advisory/proposals",
        expected_state="DRAFT",
        observed_state=create["proposal"]["current_state"],
    )
    evidence["scenarios"][-1]["proposalId"] = proposal_id

    version = _run_scenario(
        client,
        name="21_advisory_proposal_new_version.json",
        method="POST",
        path=f"/advisory/proposals/{proposal_id}/versions",
        expected_http=200,
        payload_file="21_advisory_proposal_new_version.json",
    )
    _assert(version["proposal"]["current_version_no"] == 2, "21: version increment failed")
    evidence["scenarios"].append(
        {
            "name": "21_advisory_proposal_new_version.json",
            "path": "/advisory/proposals/{proposal_id}/versions",
            "expectedVersionNo": 2,
            "observedVersionNo": version["proposal"]["current_version_no"],
        }
    )

    lifecycle_steps = [
        (
            "22_advisory_proposal_transition_to_compliance.json",
            "transitions",
            "COMPLIANCE_REVIEW",
        ),
        (
            "24_advisory_proposal_approval_compliance.json",
            "approvals",
            "AWAITING_CLIENT_CONSENT",
        ),
        (
            "23_advisory_proposal_approval_client_consent.json",
            "approvals",
            "EXECUTION_READY",
        ),
        (
            "25_advisory_proposal_transition_executed.json",
            "transitions",
            "EXECUTED",
        ),
    ]
    for file_name, endpoint, expected_state in lifecycle_steps:
        body = _run_scenario(
            client,
            name=file_name,
            method="POST",
            path=f"/advisory/proposals/{proposal_id}/{endpoint}",
            expected_http=200,
            payload_file=file_name,
        )
        _assert(body["current_state"] == expected_state, f"{file_name}: unexpected state")
        _record_state_scenario(
            evidence,
            name=file_name,
            path=f"/advisory/proposals/{{proposal_id}}/{endpoint}",
            expected_state=expected_state,
            observed_state=body["current_state"],
        )

    listed = _run_scenario(
        client,
        name="list_proposals",
        method="GET",
        path="/advisory/proposals?portfolio_id=pf_demo_lifecycle_1&limit=5",
        expected_http=200,
    )
    _assert(len(listed.get("items", [])) >= 1, "list_proposals: expected at least one item")
    evidence["domainAssertions"].append(
        {
            "name": "list_proposals",
            "minimumItems": 1,
            "observedItems": len(listed.get("items", [])),
        }
    )


def run_demo_pack(base_url: str, output: Path | None = None) -> dict[str, Any]:
    evidence = _new_evidence(base_url)
    try:
        with httpx.Client(base_url=base_url, timeout=httpx.Timeout(30.0)) as client:
            _certify_foundation(client, evidence)
            _certify_simulation_scenarios(client, evidence)
            _certify_artifact_scenario(client, evidence)
            _certify_lifecycle_scenarios(client, evidence)
        evidence["status"] = "passed"
        print(f"Demo pack validation passed for {base_url}")
        return evidence
    except Exception as exc:
        evidence["status"] = "failed"
        evidence["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        if output:
            _write_json(output, evidence)
            print(f"Wrote demo certification evidence: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run live demo pack scenarios against API base URL"
    )
    parser.add_argument(
        "--base-url", required=True, help="API base URL, for example http://127.0.0.1:8001"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional machine-readable evidence JSON path.",
    )
    args = parser.parse_args()
    run_demo_pack(args.base_url, output=args.output)
