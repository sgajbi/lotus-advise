import json

from scripts.live_runtime_decision_summary import LiveDecisionSnapshot
from scripts.live_runtime_proposal_alternatives import LiveProposalAlternativesSnapshot
from scripts.live_runtime_suite_artifacts import (
    build_markdown_summary,
    build_pr_summary,
    resolve_bundle_dir,
    result_to_json_dict,
    write_live_runtime_suite_artifact,
    write_live_runtime_suite_bundle,
    write_pr_summary_for_bundle,
)
from scripts.run_live_runtime_evidence_bundle import main as run_live_runtime_evidence_bundle_main
from scripts.validate_cross_service_parity_live import LiveParityResult
from scripts.validate_degraded_runtime_live import DegradedRuntimeResult
from scripts.validate_live_runtime_suite import (
    LiveRuntimeSuiteResult,
    validate_live_runtime_suite,
)


def _decision_snapshot(
    *,
    path_name: str,
    top_level_status: str,
    decision_status: str,
    primary_reason_code: str,
    recommended_next_action: str,
    approval_requirement_types: tuple[str, ...] = (),
) -> LiveDecisionSnapshot:
    return LiveDecisionSnapshot(
        path_name=path_name,
        top_level_status=top_level_status,
        decision_status=decision_status,
        primary_reason_code=primary_reason_code,
        recommended_next_action=recommended_next_action,
        approval_requirement_types=approval_requirement_types,
    )


def _alternatives_snapshot(
    *,
    path_name: str,
    requested_objectives: tuple[str, ...],
    feasible_count: int,
    feasible_with_review_count: int,
    rejected_count: int,
    top_ranked_alternative_id: str | None,
    top_ranked_objective: str | None,
    top_ranked_reason_codes: tuple[str, ...] = (),
    rejected_reason_codes: tuple[str, ...] = (),
    latency_ms: float = 250.0,
    selected_alternative_id: str | None = None,
    selected_rank: int | None = None,
) -> LiveProposalAlternativesSnapshot:
    return LiveProposalAlternativesSnapshot(
        path_name=path_name,
        requested_objectives=requested_objectives,
        feasible_count=feasible_count,
        feasible_with_review_count=feasible_with_review_count,
        rejected_count=rejected_count,
        selected_alternative_id=selected_alternative_id,
        selected_rank=selected_rank,
        top_ranked_alternative_id=top_ranked_alternative_id,
        top_ranked_objective=top_ranked_objective,
        top_ranked_reason_codes=top_ranked_reason_codes,
        rejected_reason_codes=rejected_reason_codes,
        latency_ms=latency_ms,
    )


def _parity_result() -> LiveParityResult:
    return LiveParityResult(
        complete_issuer_portfolio="PB_SG_GLOBAL_BAL_001",
        degraded_issuer_portfolio="DEMO_ADV_USD_001",
        degraded_issuer_coverage_status="unavailable",
        cold_duration_ms=100.0,
        warm_duration_ms=90.0,
        changed_state_portfolio="PB_SG_GLOBAL_BAL_001",
        changed_state_security_id="FO_BOND_UST_2030",
        cross_currency_security_id="FO_FUND_BLK_ALLOC",
        non_held_security_id="SEC_FUND_EM_EQ",
        workspace_handoff_portfolio="PB_SG_GLOBAL_BAL_001",
        workspace_rationale_initial_run_id="packrun_workspace_rationale_req_001",
        workspace_rationale_replacement_run_id="packrun_workspace_rationale_req_002",
        workspace_rationale_review_state="SUPERSEDED",
        workspace_rationale_supportability_status="HISTORICAL",
        lifecycle_portfolio="PB_SG_GLOBAL_BAL_001",
        lifecycle_latest_version_no=2,
        lifecycle_current_state="EXECUTED",
        async_lifecycle_portfolio="PB_SG_GLOBAL_BAL_001",
        async_lifecycle_latest_version_no=2,
        async_lifecycle_current_state="EXECUTED",
        execution_handoff_status="REQUESTED",
        execution_terminal_status="EXECUTED",
        report_status="READY",
        ready_decision=_decision_snapshot(
            path_name="ready_path",
            top_level_status="READY",
            decision_status="REQUIRES_CLIENT_CONSENT",
            primary_reason_code="CLIENT_CONSENT_REQUIRED",
            recommended_next_action="DISCUSS_WITH_CLIENT",
            approval_requirement_types=("CLIENT_CONSENT",),
        ),
        review_decision=_decision_snapshot(
            path_name="review_path",
            top_level_status="READY",
            decision_status="REQUIRES_RISK_REVIEW",
            primary_reason_code="NEW_MEDIUM_SUITABILITY_ISSUE",
            recommended_next_action="REVIEW_RISK",
            approval_requirement_types=("RISK_REVIEW",),
        ),
        blocked_decision=_decision_snapshot(
            path_name="blocked_path",
            top_level_status="BLOCKED",
            decision_status="BLOCKED_REMEDIATION_REQUIRED",
            primary_reason_code="DATA_QUALITY_MISSING_FX",
            recommended_next_action="FIX_INPUT",
            approval_requirement_types=("DATA_REMEDIATION",),
        ),
        noop_alternatives=_alternatives_snapshot(
            path_name="no_op_path",
            requested_objectives=(
                "REDUCE_CONCENTRATION",
                "RAISE_CASH",
                "IMPROVE_CURRENCY_ALIGNMENT",
                "AVOID_RESTRICTED_PRODUCTS",
            ),
            feasible_count=2,
            feasible_with_review_count=1,
            rejected_count=1,
            top_ranked_alternative_id="alt_reduce_concentration_pb_sg_global_bal_001_sec_fund_em_eq",
            top_ranked_objective="REDUCE_CONCENTRATION",
            top_ranked_reason_codes=("STATUS_FEASIBLE", "DECISION_READY_FOR_CLIENT_REVIEW"),
            rejected_reason_codes=("ALTERNATIVE_OBJECTIVE_PENDING_CANONICAL_EVIDENCE",),
            latency_ms=812.5,
        ),
        concentration_alternatives=_alternatives_snapshot(
            path_name="concentration_path",
            requested_objectives=("REDUCE_CONCENTRATION",),
            feasible_count=1,
            feasible_with_review_count=0,
            rejected_count=0,
            top_ranked_alternative_id="alt_reduce_concentration_pb_sg_global_bal_001_sec_fund_em_eq",
            top_ranked_objective="REDUCE_CONCENTRATION",
            top_ranked_reason_codes=("STATUS_FEASIBLE", "LOWER_TURNOVER_TIEBREAKER"),
            latency_ms=415.0,
        ),
        cash_raise_alternatives=_alternatives_snapshot(
            path_name="cash_raise_path",
            requested_objectives=("RAISE_CASH",),
            feasible_count=1,
            feasible_with_review_count=0,
            rejected_count=0,
            top_ranked_alternative_id="alt_raise_cash_pb_sg_global_bal_001_fo_bond_ust_2030",
            top_ranked_objective="RAISE_CASH",
            top_ranked_reason_codes=("STATUS_FEASIBLE",),
            latency_ms=521.5,
        ),
        cross_currency_alternatives=_alternatives_snapshot(
            path_name="cross_currency_path",
            requested_objectives=("IMPROVE_CURRENCY_ALIGNMENT",),
            feasible_count=1,
            feasible_with_review_count=0,
            rejected_count=0,
            top_ranked_alternative_id="alt_improve_currency_alignment_pb_sg_global_bal_001_fo_fund_blk_alloc",
            top_ranked_objective="IMPROVE_CURRENCY_ALIGNMENT",
            top_ranked_reason_codes=("STATUS_FEASIBLE",),
            latency_ms=544.0,
        ),
        restricted_product_alternatives=_alternatives_snapshot(
            path_name="restricted_product_path",
            requested_objectives=("AVOID_RESTRICTED_PRODUCTS",),
            feasible_count=0,
            feasible_with_review_count=0,
            rejected_count=1,
            top_ranked_alternative_id=None,
            top_ranked_objective=None,
            rejected_reason_codes=("ALTERNATIVE_OBJECTIVE_PENDING_CANONICAL_EVIDENCE",),
            latency_ms=118.0,
        ),
    )


def _degraded_result() -> DegradedRuntimeResult:
    return DegradedRuntimeResult(
        risk_drill_portfolio="PB_SG_GLOBAL_BAL_001",
        risk_degraded_reason="LOTUS_RISK_DEPENDENCY_UNAVAILABLE",
        core_degraded_reason="LOTUS_CORE_DEPENDENCY_UNAVAILABLE",
        fallback_mode="NONE",
        insufficient_evidence_decision=_decision_snapshot(
            path_name="insufficient_evidence_path",
            top_level_status="READY",
            decision_status="INSUFFICIENT_EVIDENCE",
            primary_reason_code="MISSING_RISK_LENS",
            recommended_next_action="REVIEW_RISK",
        ),
        risk_unavailable_alternatives=_alternatives_snapshot(
            path_name="risk_unavailable_alternatives_path",
            requested_objectives=(
                "REDUCE_CONCENTRATION",
                "RAISE_CASH",
                "IMPROVE_CURRENCY_ALIGNMENT",
            ),
            feasible_count=0,
            feasible_with_review_count=0,
            rejected_count=3,
            top_ranked_alternative_id=None,
            top_ranked_objective=None,
            rejected_reason_codes=("LOTUS_RISK_ENRICHMENT_UNAVAILABLE",),
            latency_ms=932.0,
        ),
        core_unavailable_alternatives=_alternatives_snapshot(
            path_name="core_unavailable_alternatives_path",
            requested_objectives=(
                "REDUCE_CONCENTRATION",
                "RAISE_CASH",
                "IMPROVE_CURRENCY_ALIGNMENT",
            ),
            feasible_count=0,
            feasible_with_review_count=0,
            rejected_count=0,
            top_ranked_alternative_id=None,
            top_ranked_objective=None,
            rejected_reason_codes=("LOTUS_CORE_SIMULATION_UNAVAILABLE",),
            latency_ms=0.0,
        ),
    )


def test_live_runtime_suite_runs_parity_before_degraded(monkeypatch):
    calls: list[str] = []

    def _parity():
        calls.append("parity")
        return _parity_result()

    def _degraded():
        calls.append("degraded")
        return _degraded_result()

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
        return _parity_result()

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
        return _parity_result()

    def _degraded():
        return _degraded_result()

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
    assert payload["parity"]["cross_currency_security_id"] == "FO_FUND_BLK_ALLOC"
    assert payload["parity"]["non_held_security_id"] == "SEC_FUND_EM_EQ"
    assert payload["parity"]["workspace_rationale_initial_run_id"] == (
        "packrun_workspace_rationale_req_001"
    )
    assert payload["parity"]["workspace_rationale_replacement_run_id"] == (
        "packrun_workspace_rationale_req_002"
    )
    assert payload["parity"]["workspace_rationale_review_state"] == "SUPERSEDED"
    assert payload["parity"]["workspace_rationale_supportability_status"] == "HISTORICAL"
    assert payload["parity"]["async_lifecycle_current_state"] == "EXECUTED"
    assert payload["parity"]["review_decision"]["decision_status"] == "REQUIRES_RISK_REVIEW"
    assert payload["parity"]["noop_alternatives"]["feasible_count"] == 2
    assert payload["parity"]["restricted_product_alternatives"]["rejected_reason_codes"] == [
        "ALTERNATIVE_OBJECTIVE_PENDING_CANONICAL_EVIDENCE"
    ]
    assert payload["degraded"]["core_degraded_reason"] == "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"
    assert (
        payload["degraded"]["insufficient_evidence_decision"]["primary_reason_code"]
        == "MISSING_RISK_LENS"
    )
    assert payload["degraded"]["risk_unavailable_alternatives"]["rejected_reason_codes"] == [
        "LOTUS_RISK_ENRICHMENT_UNAVAILABLE"
    ]

    output_path = tmp_path / "artifacts" / "live-runtime-suite.json"
    write_live_runtime_suite_artifact(result, output_path=str(output_path))

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written == payload


def test_live_runtime_suite_writes_timestamped_evidence_bundle(monkeypatch, tmp_path):
    def _parity():
        return _parity_result()

    def _degraded():
        return _degraded_result()

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
    assert "## Decision Paths" in summary_text
    assert "## Proposal Alternatives Paths" in summary_text
    assert "## Degraded Runtime" in summary_text
    assert "## Insufficient Evidence Path" in summary_text
    assert "## Degraded Alternatives Paths" in summary_text
    assert "async lifecycle current state" in summary_text
    assert "changed-state security" in summary_text
    assert "cross-currency security" in summary_text
    assert "non-held security" in summary_text
    assert "workspace rationale initial run" in summary_text
    assert "workspace rationale review state" in summary_text
    assert "decision status: `REQUIRES_RISK_REVIEW`" in summary_text
    assert "requested objectives: `REDUCE_CONCENTRATION`, `RAISE_CASH`" in summary_text
    assert "top ranked objective: `REDUCE_CONCENTRATION`" in summary_text
    assert "rejected reasons: `LOTUS_RISK_ENRICHMENT_UNAVAILABLE`" in summary_text


def test_live_runtime_bundle_helpers_select_latest_bundle_and_render_pr_summary(tmp_path):
    older_bundle = tmp_path / "live-runtime-suite-20260408T000001Z"
    newer_bundle = tmp_path / "live-runtime-suite-20260408T000002Z"
    older_bundle.mkdir()
    newer_bundle.mkdir()
    payload = result_to_json_dict(
        LiveRuntimeSuiteResult(parity=_parity_result(), degraded=_degraded_result())
    )
    payload["parity"]["report_status"] = "UNAVAILABLE"
    (older_bundle / "result.json").write_text(json.dumps(payload), encoding="utf-8")
    (newer_bundle / "result.json").write_text(json.dumps(payload), encoding="utf-8")

    resolved = resolve_bundle_dir(tmp_path)
    summary = build_pr_summary(tmp_path)

    assert resolved == newer_bundle
    assert "## Live Runtime Evidence" in summary
    assert f"- bundle: `{newer_bundle}`" in summary
    assert "- changed-state risk parity: `PB_SG_GLOBAL_BAL_001` via `FO_BOND_UST_2030`" in summary
    assert "- cross-currency changed-state parity: `FO_FUND_BLK_ALLOC`" in summary
    assert "- non-held changed-state parity: `SEC_FUND_EM_EQ`" in summary
    assert (
        "- workspace rationale lineage: "
        "`packrun_workspace_rationale_req_001` -> "
        "`packrun_workspace_rationale_req_002`"
    ) in summary
    assert "- workspace rationale final posture: `SUPERSEDED` / `HISTORICAL`" in summary
    assert "- async lifecycle: `EXECUTED` at version `2`" in summary
    assert "- review path: `REQUIRES_RISK_REVIEW` / `NEW_MEDIUM_SUITABILITY_ISSUE`" in summary
    assert "- insufficient-evidence path: `INSUFFICIENT_EVIDENCE` / `MISSING_RISK_LENS`" in summary
    assert "- no-op path: `2` feasible, `1` with review, top=`REDUCE_CONCENTRATION`" in summary
    assert "LOTUS_CORE_SIMULATION_UNAVAILABLE" in summary


def test_write_pr_summary_for_bundle_defaults_to_bundle_path(tmp_path):
    bundle_dir = tmp_path / "live-runtime-suite-20260408T000002Z"
    bundle_dir.mkdir()
    payload = result_to_json_dict(
        LiveRuntimeSuiteResult(parity=_parity_result(), degraded=_degraded_result())
    )
    payload["parity"]["report_status"] = "UNAVAILABLE"
    (bundle_dir / "result.json").write_text(json.dumps(payload), encoding="utf-8")

    output_path = write_pr_summary_for_bundle(bundle_dir)

    assert output_path == bundle_dir / "pr-summary.md"
    assert output_path.read_text(encoding="utf-8").startswith("## Live Runtime Evidence")


def test_run_live_runtime_evidence_bundle_writes_bundle_and_pr_summary(
    monkeypatch, tmp_path, capsys
):
    def _validate(*, include_degraded: bool = True):
        assert include_degraded is False
        return LiveRuntimeSuiteResult(
            parity=_parity_result(),
            degraded=DegradedRuntimeResult(
                risk_drill_portfolio="SKIPPED",
                risk_degraded_reason="SKIPPED",
                core_degraded_reason="SKIPPED",
                fallback_mode="SKIPPED",
                insufficient_evidence_decision=_decision_snapshot(
                    path_name="insufficient_evidence_path",
                    top_level_status="SKIPPED",
                    decision_status="SKIPPED",
                    primary_reason_code="SKIPPED",
                    recommended_next_action="SKIPPED",
                ),
                risk_unavailable_alternatives=_alternatives_snapshot(
                    path_name="risk_unavailable_alternatives_path",
                    requested_objectives=(),
                    feasible_count=0,
                    feasible_with_review_count=0,
                    rejected_count=0,
                    top_ranked_alternative_id=None,
                    top_ranked_objective=None,
                ),
                core_unavailable_alternatives=_alternatives_snapshot(
                    path_name="core_unavailable_alternatives_path",
                    requested_objectives=(),
                    feasible_count=0,
                    feasible_with_review_count=0,
                    rejected_count=0,
                    top_ranked_alternative_id=None,
                    top_ranked_objective=None,
                ),
            ),
        )

    monkeypatch.setattr(
        "scripts.run_live_runtime_evidence_bundle.validate_live_runtime_suite",
        _validate,
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_live_runtime_evidence_bundle.py",
            "--output-dir",
            str(tmp_path),
            "--skip-degraded",
        ],
    )

    run_live_runtime_evidence_bundle_main()
    output = capsys.readouterr().out
    bundle_dir = resolve_bundle_dir(tmp_path)

    assert "Live runtime evidence bundle written" in output
    assert (bundle_dir / "result.json").exists()
    assert (bundle_dir / "summary.md").exists()
    assert (bundle_dir / "pr-summary.md").exists()
