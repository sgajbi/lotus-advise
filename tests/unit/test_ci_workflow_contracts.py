from pathlib import Path

WORKFLOW_ROOT = Path(".github/workflows")


def _workflow_text(name: str) -> str:
    return (WORKFLOW_ROOT / name).read_text(encoding="utf-8")


def _workflow_job_section(workflow: str, job_id: str) -> str:
    start = workflow.index(f"  {job_id}:")
    next_job = workflow.find("\n  ", start + 1)
    while next_job != -1 and workflow[next_job + 3] == " ":
        next_job = workflow.find("\n  ", next_job + 1)
    if next_job == -1:
        return workflow[start:]
    return workflow[start:next_job]


def _assert_default_ci_guardrails(workflow: str) -> None:
    assert "concurrency:" in workflow
    assert "group: ${{ github.workflow }}-${{ github.ref }}" in workflow
    assert "cancel-in-progress: true" in workflow
    assert "permissions:\n  contents: read" in workflow


def _workflow_job_ids(workflow: str) -> list[str]:
    job_section = workflow.split("\njobs:\n", maxsplit=1)[1]
    return [
        line.strip()[:-1]
        for line in job_section.splitlines()
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":")
    ]


def _assert_all_jobs_have_timeout(workflow: str) -> None:
    for job_id in _workflow_job_ids(workflow):
        assert "timeout-minutes:" in _workflow_job_section(workflow, job_id), job_id


def _assert_governance_job_runs_baseline_freshness(workflow: str, job_id: str) -> None:
    governance_section = _workflow_job_section(workflow, job_id)

    assert "Quality Baseline Freshness" in governance_section
    assert "run: make quality-baseline-check" in governance_section


def _makefile_target_dependencies(makefile: str, target: str) -> set[str]:
    prefix = f"{target}: "
    for line in makefile.splitlines():
        if line.startswith(prefix):
            return set(line.removeprefix(prefix).split())
    raise AssertionError(f"Missing Makefile target: {target}")


def test_local_ci_targets_enforce_quality_baseline_freshness() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")

    for target in ("check", "ci", "ci-local"):
        assert "quality-baseline-check" in _makefile_target_dependencies(makefile, target)


def test_lint_enforces_refactored_complexity_gate_for_ci_lanes() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "$(MAKE) refactored-complexity-gate" in makefile
    assert "refactored-complexity-gate" in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/integrations/lotus_risk/enrichment.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/core/tactical_house_view.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/core/policy_packs/workflow_projection.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/core/advisory/narrative_ai.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/core/proposals/execution_status.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/integrations/lotus_core/stateful_context_translation.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/core/proposals/async_operations.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/core/proposals/async_operation_runner.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/core/proposals/async_payloads.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/core/proposals/command_validation.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/integrations/lotus_core/stateful_context_market_data.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/core/bank_demo_proof/artifact_refs.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/core/proposals/async_replay.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/core/common/canonical.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/core/proposals/idempotency.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/core/common/intent_dependencies.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/core/advisory_copilot/record_text.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/core/advisory_copilot/run_replay_policy.py --fail-rank B"
    ) in makefile
    assert (
        "python scripts/radon_complexity_gate.py --source-path "
        "src/integrations/lotus_ai/runtime_config.py --fail-rank B"
    ) in makefile

    for workflow_name in ("feature-lane.yml", "pr-merge-gate.yml", "main-releasability.yml"):
        workflow = _workflow_text(workflow_name)
        assert "run: make lint" in workflow


def test_ci_workflow_jobs_are_bounded_by_timeouts() -> None:
    for workflow_path in WORKFLOW_ROOT.glob("*.yml"):
        _assert_all_jobs_have_timeout(workflow_path.read_text(encoding="utf-8"))


def test_demo_assurance_gate_covers_demo_critical_evidence() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert _makefile_target_dependencies(makefile, "demo-assurance-gate") == {
        "openapi-gate",
        "no-alias-gate",
        "api-vocabulary-gate",
        "domain-data-products-gate",
        "observability-diagnostics",
        "advisory-domain-golden-regressions",
    }


def _assert_governance_job_runs_demo_assurance_checks(workflow: str, job_id: str) -> None:
    governance_section = _workflow_job_section(workflow, job_id)

    assert "run: make openapi-gate" in governance_section
    assert "run: make api-vocabulary-gate" in governance_section
    assert governance_section.index("Quality Baseline Freshness") < governance_section.index(
        "Checkout Lotus Platform Contracts"
    )
    assert "Checkout Lotus Platform Contracts" in governance_section
    assert "repository: sgajbi/lotus-platform" in governance_section
    assert "path: lotus-platform" in governance_section
    assert "LOTUS_PLATFORM_ROOT: ${{ github.workspace }}/lotus-platform" in governance_section
    assert "run: make domain-data-products-gate" in governance_section
    assert "run: make observability-diagnostics" in governance_section
    assert "run: make advisory-domain-golden-regressions" in governance_section


def test_pytest_configuration_has_single_authoritative_file() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    pytest_ini = Path("pytest.ini").read_text(encoding="utf-8")

    assert "[tool.pytest.ini_options]" not in pyproject
    assert "[pytest]" in pytest_ini
    assert "testpaths =" in pytest_ini
    assert "addopts = --strict-markers" in pytest_ini


def test_mypy_configuration_has_no_unused_override_sections() -> None:
    mypy_config = Path("mypy.ini").read_text(encoding="utf-8")

    assert "warn_unused_configs = True" in mypy_config
    assert "[mypy-tests.*]" not in mypy_config
    assert "[mypy-scripts.*]" not in mypy_config


def test_feature_lane_unit_tests_run_in_parallel_with_static_governance() -> None:
    workflow = _workflow_text("feature-lane.yml")

    unit_section = _workflow_job_section(workflow, "unit-tests")

    _assert_default_ci_guardrails(workflow)
    _assert_governance_job_runs_baseline_freshness(workflow, "lint-dependency-governance")
    _assert_governance_job_runs_demo_assurance_checks(workflow, "lint-dependency-governance")
    assert "Feature Lane / Tests (unit)" in unit_section
    assert "needs:" not in unit_section
    assert "Feature Lane / Lint Dependency Governance" in workflow


def test_pr_and_main_runtime_jobs_are_parallelized_without_renaming_required_checks() -> None:
    for workflow_name, lane_name, coverage_artifact_prefix in (
        ("pr-merge-gate.yml", "PR Merge Gate", "coverage-data-"),
        ("main-releasability.yml", "Main Releasability", "main-releasability-coverage-data-"),
    ):
        workflow = _workflow_text(workflow_name)

        _assert_default_ci_guardrails(workflow)
        _assert_governance_job_runs_baseline_freshness(workflow, "lint-typecheck-governance")
        _assert_governance_job_runs_demo_assurance_checks(workflow, "lint-typecheck-governance")
        assert f"{lane_name} / Lint Typecheck Governance" in workflow
        assert f"{lane_name} / Tests (${{{{ matrix.suite }}}})" in workflow
        assert f"{lane_name} / Coverage Gate (Combined)" in workflow
        assert f"{lane_name} / Validate Docker Build" in workflow

        for job_id in (
            "test-suites",
            "postgres-migration-smoke",
            "production-profile-smoke",
            "production-profile-guardrail-negatives",
        ):
            job_section = _workflow_job_section(workflow, job_id)
            assert "needs: [lint-typecheck-governance]" not in job_section

        docker_section = _workflow_job_section(workflow, "docker-build")
        assert (
            "needs: [coverage-gate, postgres-migration-smoke, production-profile-smoke, "
            "production-profile-guardrail-negatives]"
        ) in docker_section

        coverage_section = _workflow_job_section(workflow, "coverage-gate")
        assert "needs: [test-suites]" in coverage_section
        assert f"pattern: {coverage_artifact_prefix}*" in coverage_section

        test_section = _workflow_job_section(workflow, "test-suites")
        assert f"name: {coverage_artifact_prefix}${{{{ matrix.suite }}}}" in test_section
        assert "include-hidden-files: true" in test_section
        assert "if-no-files-found: error" in test_section


def test_nightly_postgres_demo_pack_declares_controlled_ci_fallback() -> None:
    workflow = _workflow_text("nightly-postgres-full.yml")

    _assert_default_ci_guardrails(workflow)
    assert "ENVIRONMENT: ci" in workflow
    assert 'LOTUS_ADVISE_ALLOW_LOCAL_SIMULATION_FALLBACK: "true"' in workflow
    assert "python scripts/run_demo_pack_live.py --base-url http://127.0.0.1:8010" in workflow


def test_pull_request_target_auto_merge_is_guarded_to_internal_labeled_prs() -> None:
    workflow = _workflow_text("pr-auto-merge.yml")
    auto_merge_section = _workflow_job_section(workflow, "queue-auto-merge")

    assert "pull_request_target:" in workflow
    assert "permissions:\n  contents: write\n  pull-requests: write" in workflow
    assert "github.event.pull_request.base.ref == 'main'" in auto_merge_section
    assert "github.event.pull_request.head.repo.fork == false" in auto_merge_section
    assert "contains(github.event.pull_request.labels.*.name, 'automerge')" in auto_merge_section
    assert 'gh api "repos/$GITHUB_REPOSITORY/branches/main"' in auto_merge_section
    assert 'payload.get("protected") is not True' in auto_merge_section
    assert 'protection.get("required_status_checks")' in auto_merge_section
    assert "main branch must require status checks before auto-merge can be queued" in (
        auto_merge_section
    )
    assert 'gh pr merge "$PR_NUMBER" --repo "$GITHUB_REPOSITORY" --auto --merge' in (
        auto_merge_section
    )
