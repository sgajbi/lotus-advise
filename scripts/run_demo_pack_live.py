import argparse
import json
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "docs" / "demo"


class DemoRunError(RuntimeError):
    pass


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


def run_demo_pack(base_url: str) -> None:
    timeout = httpx.Timeout(30.0)
    with httpx.Client(base_url=base_url, timeout=timeout) as client:
        # DPM single-run demos
        dpm_files = [
            "01_standard_drift.json",
            "02_sell_to_fund.json",
            "03_multi_currency_fx.json",
            "04_safety_sell_only.json",
            "05_safety_hard_block_price.json",
            "06_tax_aware_hifo.json",
            "07_settlement_overdraft_block.json",
            "08_solver_mode.json",
        ]
        for index, expected in [
            (1, "READY"),
            (2, "READY"),
            (3, "READY"),
            (4, "PENDING_REVIEW"),
            (5, "BLOCKED"),
            (6, "READY"),
            (7, "BLOCKED"),
            (8, "READY"),
        ]:
            file_name = dpm_files[index - 1]
            body = _run_scenario(
                client,
                name=file_name,
                method="POST",
                path="/rebalance/simulate",
                expected_http=200,
                payload_file=file_name,
                headers={"Idempotency-Key": f"live-demo-{index:02d}"},
            )
            _assert(
                body.get("status") == expected,
                f"{file_name}: unexpected status {body.get('status')}",
            )

        supportability = _run_scenario(
            client,
            name="27_dpm_supportability_artifact_flow.json",
            method="POST",
            path="/rebalance/simulate",
            expected_http=200,
            payload_file="27_dpm_supportability_artifact_flow.json",
            headers={
                "Idempotency-Key": "live-demo-27-supportability",
                "X-Correlation-Id": "live-corr-27-supportability",
            },
        )
        run_id = supportability["rebalance_run_id"]

        by_run = _run_scenario(
            client,
            name="27_get_run",
            method="GET",
            path=f"/rebalance/runs/{run_id}",
            expected_http=200,
        )
        _assert(by_run["rebalance_run_id"] == run_id, "27: run lookup mismatch")

        by_correlation = _run_scenario(
            client,
            name="27_get_run_by_correlation",
            method="GET",
            path="/rebalance/runs/by-correlation/live-corr-27-supportability",
            expected_http=200,
        )
        _assert(by_correlation["rebalance_run_id"] == run_id, "27: correlation lookup mismatch")

        by_idempotency = _run_scenario(
            client,
            name="27_get_run_by_idempotency",
            method="GET",
            path="/rebalance/runs/idempotency/live-demo-27-supportability",
            expected_http=200,
        )
        _assert(by_idempotency["rebalance_run_id"] == run_id, "27: idempotency lookup mismatch")

        artifact_one = _run_scenario(
            client,
            name="27_get_artifact_one",
            method="GET",
            path=f"/rebalance/runs/{run_id}/artifact",
            expected_http=200,
        )
        artifact_two = _run_scenario(
            client,
            name="27_get_artifact_two",
            method="GET",
            path=f"/rebalance/runs/{run_id}/artifact",
            expected_http=200,
        )
        _assert(
            artifact_one["evidence"]["hashes"]["artifact_hash"]
            == artifact_two["evidence"]["hashes"]["artifact_hash"],
            "27: artifact hash not deterministic",
        )

        # Batch demo
        batch = _run_scenario(
            client,
            name="09_batch_what_if_analysis.json",
            method="POST",
            path="/rebalance/analyze",
            expected_http=200,
            payload_file="09_batch_what_if_analysis.json",
        )
        _assert(
            set(batch.get("results", {}).keys()) == {"baseline", "tax_budget", "settlement_guard"},
            "09_batch_what_if_analysis.json: unexpected scenario keys",
        )

        async_batch = _run_scenario(
            client,
            name="26_dpm_async_batch_analysis.json",
            method="POST",
            path="/rebalance/analyze/async",
            expected_http=202,
            payload_file="26_dpm_async_batch_analysis.json",
            headers={"X-Correlation-Id": "demo-corr-26-async"},
        )
        operation_id = async_batch["operation_id"]
        operation = _run_scenario(
            client,
            name="get_async_operation",
            method="GET",
            path=f"/rebalance/operations/{operation_id}",
            expected_http=200,
        )
        _assert(operation["status"] == "SUCCEEDED", "26: async operation did not succeed")
        _assert(
            operation.get("result", {}).get("warnings") == ["PARTIAL_BATCH_FAILURE"],
            "26: expected PARTIAL_BATCH_FAILURE warning",
        )
        _assert(
            set(operation.get("result", {}).get("failed_scenarios", {}).keys())
            == {"invalid_options"},
            "26: expected invalid_options failed scenario",
        )

        # Advisory simulate demos
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
                path="/rebalance/proposals/simulate",
                expected_http=200,
                payload_file=file_name,
                headers={"Idempotency-Key": f"live-{file_name}"},
            )
            _assert(
                body.get("status") == expected,
                f"{file_name}: unexpected status {body.get('status')}",
            )

        artifact = _run_scenario(
            client,
            name="19_advisory_proposal_artifact.json",
            method="POST",
            path="/rebalance/proposals/artifact",
            expected_http=200,
            payload_file="19_advisory_proposal_artifact.json",
            headers={"Idempotency-Key": "live-demo-artifact-19"},
        )
        _assert(artifact.get("status") == "READY", "19_advisory_proposal_artifact.json: not READY")
        _assert(
            artifact.get("evidence_bundle", {})
            .get("hashes", {})
            .get("artifact_hash", "")
            .startswith("sha256:"),
            "19_advisory_proposal_artifact.json: missing artifact hash",
        )

        # Lifecycle flow demos
        create = _run_scenario(
            client,
            name="20_advisory_proposal_persist_create.json",
            method="POST",
            path="/rebalance/proposals",
            expected_http=200,
            payload_file="20_advisory_proposal_persist_create.json",
            headers={"Idempotency-Key": "live-demo-lifecycle-20"},
        )
        proposal_id = create["proposal"]["proposal_id"]
        _assert(create["proposal"]["current_state"] == "DRAFT", "20: unexpected lifecycle state")

        version = _run_scenario(
            client,
            name="21_advisory_proposal_new_version.json",
            method="POST",
            path=f"/rebalance/proposals/{proposal_id}/versions",
            expected_http=200,
            payload_file="21_advisory_proposal_new_version.json",
        )
        _assert(version["proposal"]["current_version_no"] == 2, "21: version increment failed")

        transition = _run_scenario(
            client,
            name="22_advisory_proposal_transition_to_compliance.json",
            method="POST",
            path=f"/rebalance/proposals/{proposal_id}/transitions",
            expected_http=200,
            payload_file="22_advisory_proposal_transition_to_compliance.json",
        )
        _assert(transition["current_state"] == "COMPLIANCE_REVIEW", "22: unexpected state")

        compliance = _run_scenario(
            client,
            name="24_advisory_proposal_approval_compliance.json",
            method="POST",
            path=f"/rebalance/proposals/{proposal_id}/approvals",
            expected_http=200,
            payload_file="24_advisory_proposal_approval_compliance.json",
        )
        _assert(compliance["current_state"] == "AWAITING_CLIENT_CONSENT", "24: unexpected state")

        consent = _run_scenario(
            client,
            name="23_advisory_proposal_approval_client_consent.json",
            method="POST",
            path=f"/rebalance/proposals/{proposal_id}/approvals",
            expected_http=200,
            payload_file="23_advisory_proposal_approval_client_consent.json",
        )
        _assert(consent["current_state"] == "EXECUTION_READY", "23: unexpected state")

        executed = _run_scenario(
            client,
            name="25_advisory_proposal_transition_executed.json",
            method="POST",
            path=f"/rebalance/proposals/{proposal_id}/transitions",
            expected_http=200,
            payload_file="25_advisory_proposal_transition_executed.json",
        )
        _assert(executed["current_state"] == "EXECUTED", "25: unexpected state")

        listed = _run_scenario(
            client,
            name="list_proposals",
            method="GET",
            path="/rebalance/proposals?portfolio_id=pf_demo_lifecycle_1&limit=5",
            expected_http=200,
        )
        _assert(len(listed.get("items", [])) >= 1, "list_proposals: expected at least one item")

    print(f"Demo pack validation passed for {base_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run live demo pack scenarios against API base URL"
    )
    parser.add_argument(
        "--base-url", required=True, help="API base URL, for example http://127.0.0.1:8001"
    )
    args = parser.parse_args()
    run_demo_pack(args.base_url)
