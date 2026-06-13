from pathlib import Path


def _workflow_job_section(workflow: str, job_id: str) -> str:
    start = workflow.index(f"  {job_id}:")
    next_job = workflow.find("\n  ", start + 1)
    while next_job != -1 and workflow[next_job + 3] == " ":
        next_job = workflow.find("\n  ", next_job + 1)
    if next_job == -1:
        return workflow[start:]
    return workflow[start:next_job]


def test_pytest_configuration_has_single_authoritative_file() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    pytest_ini = Path("pytest.ini").read_text(encoding="utf-8")

    assert "[tool.pytest.ini_options]" not in pyproject
    assert "[pytest]" in pytest_ini
    assert "testpaths =" in pytest_ini
    assert "addopts = --strict-markers" in pytest_ini


def test_feature_lane_unit_tests_run_in_parallel_with_static_governance() -> None:
    workflow = Path(".github/workflows/feature-lane.yml").read_text(encoding="utf-8")

    unit_section = _workflow_job_section(workflow, "unit-tests")

    assert "Feature Lane / Tests (unit)" in unit_section
    assert "needs:" not in unit_section
    assert "Feature Lane / Lint Dependency Governance" in workflow


def test_pr_and_main_runtime_jobs_are_parallelized_without_renaming_required_checks() -> None:
    for workflow_path, lane_name in (
        (Path(".github/workflows/pr-merge-gate.yml"), "PR Merge Gate"),
        (Path(".github/workflows/main-releasability.yml"), "Main Releasability"),
    ):
        workflow = workflow_path.read_text(encoding="utf-8")

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


def test_nightly_postgres_demo_pack_declares_controlled_ci_fallback() -> None:
    workflow = Path(".github/workflows/nightly-postgres-full.yml").read_text(encoding="utf-8")

    assert "ENVIRONMENT: ci" in workflow
    assert 'LOTUS_ADVISE_ALLOW_LOCAL_SIMULATION_FALLBACK: "true"' in workflow
    assert "python scripts/run_demo_pack_live.py --base-url http://127.0.0.1:8010" in workflow
