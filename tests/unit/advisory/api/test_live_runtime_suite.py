import json

from scripts.live_runtime_suite_artifacts import (
    build_markdown_summary,
    build_pr_summary,
    resolve_bundle_dir,
    result_to_json_dict,
    write_live_runtime_suite_artifact,
    write_live_runtime_suite_bundle,
)
from scripts.validate_cross_service_parity_live import LiveParityResult
from scripts.validate_degraded_runtime_live import DegradedRuntimeResult
from scripts.validate_live_runtime_suite import (
    validate_live_runtime_suite,
)


def test_live_runtime_suite_runs_parity_before_degraded(monkeypatch):
    calls: list[str] = []

    def _parity():
        calls.append("parity")
        return LiveParityResult(
            complete_issuer_portfolio="PB_SG_GLOBAL_BAL_001",
            degraded_issuer_portfolio="DEMO_ADV_USD_001",
            degraded_issuer_coverage_status="unavailable",
            cold_duration_ms=100.0,
            warm_duration_ms=90.0,
            changed_state_portfolio="PB_SG_GLOBAL_BAL_001",
            changed_state_security_id="FO_BOND_UST_2030",
            workspace_handoff_portfolio="PB_SG_GLOBAL_BAL_001",
            lifecycle_portfolio="PB_SG_GLOBAL_BAL_001",
            lifecycle_latest_version_no=2,
            lifecycle_current_state="EXECUTED",
            async_lifecycle_portfolio="PB_SG_GLOBAL_BAL_001",
            async_lifecycle_latest_version_no=2,
            async_lifecycle_current_state="EXECUTED",
            execution_handoff_status="REQUESTED",
            execution_terminal_status="EXECUTED",
            report_status="READY",
        )

    def _degraded():
        calls.append("degraded")
        return DegradedRuntimeResult(
            risk_drill_portfolio="PB_SG_GLOBAL_BAL_001",
            risk_degraded_reason="LOTUS_RISK_DEPENDENCY_UNAVAILABLE",
            core_degraded_reason="LOTUS_CORE_DEPENDENCY_UNAVAILABLE",
            fallback_mode="NONE",
        )

    monkeypatch.setattr(
        "scripts.validate_live_runtime_suite.validate_live_cross_service_parity",
        _parity,
    )
    monkeypatch.setattr(
        "scripts.validate_live_runtime_suite.validate_live_degraded_runtime",
        _degraded,
    )

    result = validate_live_runtime_suite()

    assert calls == ["parity", "degraded"]
    assert result.parity.lifecycle_current_state == "EXECUTED"
    assert result.degraded.fallback_mode == "NONE"


def test_live_runtime_suite_can_skip_degraded(monkeypatch):
    calls: list[str] = []

    def _parity():
        calls.append("parity")
        return LiveParityResult(
            complete_issuer_portfolio="PB_SG_GLOBAL_BAL_001",
            degraded_issuer_portfolio="DEMO_ADV_USD_001",
            degraded_issuer_coverage_status="unavailable",
            cold_duration_ms=100.0,
            warm_duration_ms=90.0,
            changed_state_portfolio="PB_SG_GLOBAL_BAL_001",
            changed_state_security_id="FO_BOND_UST_2030",
            workspace_handoff_portfolio="PB_SG_GLOBAL_BAL_001",
            lifecycle_portfolio="PB_SG_GLOBAL_BAL_001",
            lifecycle_latest_version_no=2,
            lifecycle_current_state="EXECUTED",
            async_lifecycle_portfolio="PB_SG_GLOBAL_BAL_001",
            async_lifecycle_latest_version_no=2,
            async_lifecycle_current_state="EXECUTED",
            execution_handoff_status="REQUESTED",
            execution_terminal_status="EXECUTED",
            report_status="READY",
        )

    def _degraded():
        calls.append("degraded")
        raise AssertionError("degraded validator should have been skipped")

    monkeypatch.setattr(
        "scripts.validate_live_runtime_suite.validate_live_cross_service_parity",
        _parity,
    )
    monkeypatch.setattr(
        "scripts.validate_live_runtime_suite.validate_live_degraded_runtime",
        _degraded,
    )

    result = validate_live_runtime_suite(include_degraded=False)

    assert calls == ["parity"]
    assert result.degraded.risk_degraded_reason == "SKIPPED"
    assert result.degraded.core_degraded_reason == "SKIPPED"


def test_live_runtime_suite_serializes_machine_readable_result(monkeypatch, tmp_path):
    def _parity():
        return LiveParityResult(
            complete_issuer_portfolio="PB_SG_GLOBAL_BAL_001",
            degraded_issuer_portfolio="DEMO_ADV_USD_001",
            degraded_issuer_coverage_status="unavailable",
            cold_duration_ms=100.0,
            warm_duration_ms=90.0,
            changed_state_portfolio="PB_SG_GLOBAL_BAL_001",
            changed_state_security_id="FO_BOND_UST_2030",
            workspace_handoff_portfolio="PB_SG_GLOBAL_BAL_001",
            lifecycle_portfolio="PB_SG_GLOBAL_BAL_001",
            lifecycle_latest_version_no=2,
            lifecycle_current_state="EXECUTED",
            async_lifecycle_portfolio="PB_SG_GLOBAL_BAL_001",
            async_lifecycle_latest_version_no=2,
            async_lifecycle_current_state="EXECUTED",
            execution_handoff_status="REQUESTED",
            execution_terminal_status="EXECUTED",
            report_status="READY",
        )

    def _degraded():
        return DegradedRuntimeResult(
            risk_drill_portfolio="PB_SG_GLOBAL_BAL_001",
            risk_degraded_reason="LOTUS_RISK_DEPENDENCY_UNAVAILABLE",
            core_degraded_reason="LOTUS_CORE_DEPENDENCY_UNAVAILABLE",
            fallback_mode="NONE",
        )

    monkeypatch.setattr(
        "scripts.validate_live_runtime_suite.validate_live_cross_service_parity",
        _parity,
    )
    monkeypatch.setattr(
        "scripts.validate_live_runtime_suite.validate_live_degraded_runtime",
        _degraded,
    )

    result = validate_live_runtime_suite()
    payload = result_to_json_dict(result)

    assert payload["parity"]["complete_issuer_portfolio"] == "PB_SG_GLOBAL_BAL_001"
    assert payload["parity"]["changed_state_security_id"] == "FO_BOND_UST_2030"
    assert payload["parity"]["async_lifecycle_current_state"] == "EXECUTED"
    assert payload["degraded"]["core_degraded_reason"] == "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"

    output_path = tmp_path / "artifacts" / "live-runtime-suite.json"
    write_live_runtime_suite_artifact(result, output_path=str(output_path))

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written == payload


def test_live_runtime_suite_writes_timestamped_evidence_bundle(monkeypatch, tmp_path):
    def _parity():
        return LiveParityResult(
            complete_issuer_portfolio="PB_SG_GLOBAL_BAL_001",
            degraded_issuer_portfolio="DEMO_ADV_USD_001",
            degraded_issuer_coverage_status="unavailable",
            cold_duration_ms=100.0,
            warm_duration_ms=90.0,
            changed_state_portfolio="PB_SG_GLOBAL_BAL_001",
            changed_state_security_id="FO_BOND_UST_2030",
            workspace_handoff_portfolio="PB_SG_GLOBAL_BAL_001",
            lifecycle_portfolio="PB_SG_GLOBAL_BAL_001",
            lifecycle_latest_version_no=2,
            lifecycle_current_state="EXECUTED",
            async_lifecycle_portfolio="PB_SG_GLOBAL_BAL_001",
            async_lifecycle_latest_version_no=2,
            async_lifecycle_current_state="EXECUTED",
            execution_handoff_status="REQUESTED",
            execution_terminal_status="EXECUTED",
            report_status="READY",
        )

    def _degraded():
        return DegradedRuntimeResult(
            risk_drill_portfolio="PB_SG_GLOBAL_BAL_001",
            risk_degraded_reason="LOTUS_RISK_DEPENDENCY_UNAVAILABLE",
            core_degraded_reason="LOTUS_CORE_DEPENDENCY_UNAVAILABLE",
            fallback_mode="NONE",
        )

    monkeypatch.setattr(
        "scripts.validate_live_runtime_suite.validate_live_cross_service_parity",
        _parity,
    )
    monkeypatch.setattr(
        "scripts.validate_live_runtime_suite.validate_live_degraded_runtime",
        _degraded,
    )

    result = validate_live_runtime_suite()
    bundle_dir = write_live_runtime_suite_bundle(result, output_dir=str(tmp_path))

    assert bundle_dir is not None
    result_json = bundle_dir / "result.json"
    summary_md = bundle_dir / "summary.md"
    assert result_json.exists()
    assert summary_md.exists()
    assert json.loads(result_json.read_text(encoding="utf-8")) == result_to_json_dict(result)
    summary_text = summary_md.read_text(encoding="utf-8")
    assert summary_text == build_markdown_summary(result)
    assert "## Parity" in summary_text
    assert "## Degraded Runtime" in summary_text
    assert "async lifecycle current state" in summary_text
    assert "changed-state security" in summary_text


def test_live_runtime_bundle_helpers_select_latest_bundle_and_render_pr_summary(tmp_path):
    older_bundle = tmp_path / "live-runtime-suite-20260408T000001Z"
    newer_bundle = tmp_path / "live-runtime-suite-20260408T000002Z"
    older_bundle.mkdir()
    newer_bundle.mkdir()
    payload = {
        "parity": {
            "complete_issuer_portfolio": "PB_SG_GLOBAL_BAL_001",
            "degraded_issuer_portfolio": "DEMO_ADV_USD_001",
            "degraded_issuer_coverage_status": "unavailable",
            "cold_duration_ms": 100.0,
            "warm_duration_ms": 90.0,
            "changed_state_portfolio": "PB_SG_GLOBAL_BAL_001",
            "changed_state_security_id": "FO_BOND_UST_2030",
            "workspace_handoff_portfolio": "PB_SG_GLOBAL_BAL_001",
            "lifecycle_portfolio": "PB_SG_GLOBAL_BAL_001",
            "lifecycle_latest_version_no": 2,
            "lifecycle_current_state": "EXECUTED",
            "async_lifecycle_portfolio": "PB_SG_GLOBAL_BAL_001",
            "async_lifecycle_latest_version_no": 2,
            "async_lifecycle_current_state": "EXECUTED",
            "execution_handoff_status": "REQUESTED",
            "execution_terminal_status": "EXECUTED",
            "report_status": "UNAVAILABLE",
        },
        "degraded": {
            "risk_drill_portfolio": "PB_SG_GLOBAL_BAL_001",
            "risk_degraded_reason": "LOTUS_RISK_DEPENDENCY_UNAVAILABLE",
            "core_degraded_reason": "LOTUS_CORE_DEPENDENCY_UNAVAILABLE",
            "fallback_mode": "NONE",
        },
    }
    (older_bundle / "result.json").write_text(json.dumps(payload), encoding="utf-8")
    (newer_bundle / "result.json").write_text(json.dumps(payload), encoding="utf-8")

    resolved = resolve_bundle_dir(tmp_path)
    summary = build_pr_summary(tmp_path)

    assert resolved == newer_bundle
    assert "## Live Runtime Evidence" in summary
    assert f"- bundle: `{newer_bundle}`" in summary
    assert "- changed-state risk parity: `PB_SG_GLOBAL_BAL_001` via `FO_BOND_UST_2030`" in summary
    assert "- async lifecycle: `EXECUTED` at version `2`" in summary
