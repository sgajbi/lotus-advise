import json
from pathlib import Path
from shutil import copy2

import pytest

from scripts.ci_lane_parity_gate import evaluate, load_policy

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_LANE_WORKFLOWS = (
    "feature-lane.yml",
    "pr-merge-gate.yml",
    "main-releasability.yml",
)


def _copy_shipped_parity_inputs(tmp_path: Path) -> dict[str, Path]:
    """Copy the policy's real lane inputs so mutations cannot alter the checkout."""

    copy2(REPOSITORY_ROOT / "Makefile", tmp_path / "Makefile")
    workflow_directory = tmp_path / ".github" / "workflows"
    workflow_directory.mkdir(parents=True)
    copied: dict[str, Path] = {}
    for name in _LANE_WORKFLOWS:
        destination = workflow_directory / name
        copy2(REPOSITORY_ROOT / ".github" / "workflows" / name, destination)
        copied[name] = destination
    return copied


def _shipped_policy() -> dict[str, object]:
    return load_policy(REPOSITORY_ROOT / "quality" / "ci-lane-parity.v1.json")


def _evaluate_shipped_inputs(tmp_path: Path) -> list[str]:
    return evaluate(
        repo_root=tmp_path,
        policy=_shipped_policy(),
        makefile=tmp_path / "Makefile",
    )


def test_ci_lane_parity_gate_counts_direct_scripts_and_unit_contract_execution(
    tmp_path: Path,
) -> None:
    (tmp_path / "Makefile").write_text(
        "check: direct-script unit-contract changed-coverage\n"
        "ci: direct-script unit-contract changed-coverage\n"
        "ci-local: direct-script unit-contract changed-coverage\n",
        encoding="utf-8",
    )
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    workflows = {
        "feature.yml": (
            "jobs:\n  checks:\n    steps:\n      - run: python scripts/direct.py\n"
            "      - run: python -m pytest tests/unit\n"
        ),
        "pr.yml": (
            "jobs:\n  checks:\n    steps:\n      - run: python scripts/direct.py\n"
            "      - run: python scripts/changed.py\n"
        ),
        "main.yml": (
            "jobs:\n  checks:\n    steps:\n      - run: python -m pytest tests/unit\n"
            "      - run: python scripts/changed.py\n"
        ),
    }
    for name, text in workflows.items():
        (workflow_dir / name).write_text(text, encoding="utf-8")
    policy = {
        "schema_version": "lotus.advise.ci-lane-parity.v1",
        "aggregate_targets": ["check", "ci", "ci-local"],
        "lanes": {
            "feature": ".github/workflows/feature.yml",
            "pr": ".github/workflows/pr.yml",
            "main": ".github/workflows/main.yml",
        },
        "controls": [
            {
                "target": "direct-script",
                "lane_signals": {
                    "feature": ["scripts/direct.py"],
                    "pr": ["scripts/direct.py"],
                },
            },
            {
                "target": "unit-contract",
                "lane_signals": {
                    "feature": ["tests/unit"],
                    "main": ["tests/unit"],
                },
            },
            {
                "target": "changed-coverage",
                "lane_signals": {
                    "pr": ["scripts/changed.py"],
                    "main": ["scripts/changed.py"],
                },
            },
        ],
    }
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        json.dumps(policy),
        encoding="utf-8",
    )
    parsed_policy = load_policy(policy_path)
    assert evaluate(repo_root=tmp_path, policy=parsed_policy, makefile=tmp_path / "Makefile") == []
    (tmp_path / "Makefile").write_text(
        "check: direct-script unit-contract changed-coverage\n"
        "ci: direct-script unit-contract changed-coverage\n"
        "ci-local: direct-script unit-contract\n",
        encoding="utf-8",
    )
    failures = evaluate(
        repo_root=tmp_path,
        policy=parsed_policy,
        makefile=tmp_path / "Makefile",
    )
    assert "changed-coverage missing from ci-local" in failures[0]


@pytest.mark.parametrize(
    "mutation",
    [
        "jobs:\n  checks:\n    steps: []\n",
        (
            "jobs:\n  checks:\n    steps:\n      # - run: make quality-trend-gate\n"
            "      - run: make lint\n"
        ),
        "jobs:\n  checks:\n    steps:\n      - run: echo 'make quality-trend-gate'\n",
        "jobs:\n  checks:\n    steps:\n      - run: make quality-trend-gate --dry-run\n",
        (
            "jobs:\n  checks:\n    env: {MAKEFLAGS: --dry-run}\n"
            "    steps:\n      - run: make quality-trend-gate\n"
        ),
    ],
)
def test_ci_lane_parity_rejects_removed_commented_and_echoed_controls(
    tmp_path: Path,
    mutation: str,
) -> None:
    (tmp_path / "Makefile").write_text(
        "check: quality-trend-gate\nci: quality-trend-gate\nci-local: quality-trend-gate\n",
        encoding="utf-8",
    )
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    real_workflow = "jobs:\n  checks:\n    steps:\n      - run: make quality-trend-gate\n"
    for name in ("feature.yml", "pr.yml", "main.yml"):
        (workflow_dir / name).write_text(real_workflow, encoding="utf-8")
    policy = {
        "schema_version": "lotus.advise.ci-lane-parity.v1",
        "aggregate_targets": ["check", "ci", "ci-local"],
        "lanes": {
            "feature": ".github/workflows/feature.yml",
            "pr": ".github/workflows/pr.yml",
            "main": ".github/workflows/main.yml",
        },
        "controls": [
            {
                "target": "quality-trend-gate",
                "lane_signals": {
                    "feature": ["make quality-trend-gate"],
                    "pr": ["make quality-trend-gate"],
                    "main": ["make quality-trend-gate"],
                },
            }
        ],
    }
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    parsed_policy = load_policy(policy_path)
    assert evaluate(repo_root=tmp_path, policy=parsed_policy, makefile=tmp_path / "Makefile") == []

    (workflow_dir / "main.yml").write_text(mutation, encoding="utf-8")
    failures = evaluate(repo_root=tmp_path, policy=parsed_policy, makefile=tmp_path / "Makefile")

    assert failures == ["CI lane parity missing executable evidence for quality-trend-gate in main"]


def test_ci_lane_parity_does_not_pair_echoed_test_path_with_another_pytest_command(
    tmp_path: Path,
) -> None:
    (tmp_path / "Makefile").write_text(
        "check: unit-contract\nci: unit-contract\nci-local: unit-contract\n",
        encoding="utf-8",
    )
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    workflow = (
        "jobs:\n  checks:\n    steps:\n      - run: python -m pytest tests/integration\n"
        "      - run: echo tests/unit\n"
    )
    for name in ("feature.yml", "pr.yml", "main.yml"):
        (workflow_dir / name).write_text(workflow, encoding="utf-8")
    policy = {
        "schema_version": "lotus.advise.ci-lane-parity.v1",
        "aggregate_targets": ["check", "ci", "ci-local"],
        "lanes": {"feature": ".github/workflows/feature.yml"},
        "controls": [{"target": "unit-contract", "lane_signals": {"feature": ["tests/unit"]}}],
    }

    assert evaluate(repo_root=tmp_path, policy=policy, makefile=tmp_path / "Makefile") == [
        "CI lane parity missing executable evidence for unit-contract in feature"
    ]


def test_ci_lane_parity_requires_matrix_path_in_the_pytest_command(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text(
        "check: unit-contract\nci: unit-contract\nci-local: unit-contract\n",
        encoding="utf-8",
    )
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    workflow = (
        "jobs:\n  checks:\n    strategy:\n      matrix:\n        path: tests/unit\n"
        "    steps:\n      - run: python -m pytest tests/integration\n"
        "      - run: echo ${{ matrix.path }}\n"
    )
    (workflow_dir / "feature.yml").write_text(workflow, encoding="utf-8")
    policy = {
        "schema_version": "lotus.advise.ci-lane-parity.v1",
        "aggregate_targets": ["check", "ci", "ci-local"],
        "lanes": {"feature": ".github/workflows/feature.yml"},
        "controls": [{"target": "unit-contract", "lane_signals": {"feature": ["tests/unit"]}}],
    }

    assert evaluate(repo_root=tmp_path, policy=policy, makefile=tmp_path / "Makefile") == [
        "CI lane parity missing executable evidence for unit-contract in feature"
    ]


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("python scripts/changed.py", []),
        ("uv run python scripts/changed.py", []),
        (
            "python -c 'pass' scripts/changed.py",
            ["CI lane parity missing executable evidence for script-control in feature"],
        ),
        (
            "uv run python -m http.server scripts/changed.py",
            ["CI lane parity missing executable evidence for script-control in feature"],
        ),
    ],
)
def test_ci_lane_parity_requires_script_at_python_program_position(
    tmp_path: Path, command: str, expected: list[str]
) -> None:
    (tmp_path / "Makefile").write_text(
        "check: script-control\nci: script-control\nci-local: script-control\n",
        encoding="utf-8",
    )
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "feature.yml").write_text(
        f"jobs:\n  checks:\n    steps:\n      - run: {command}\n",
        encoding="utf-8",
    )
    policy = {
        "schema_version": "lotus.advise.ci-lane-parity.v1",
        "aggregate_targets": ["check", "ci", "ci-local"],
        "lanes": {"feature": ".github/workflows/feature.yml"},
        "controls": [
            {
                "target": "script-control",
                "lane_signals": {"feature": ["scripts/changed.py"]},
            }
        ],
    }

    assert evaluate(repo_root=tmp_path, policy=policy, makefile=tmp_path / "Makefile") == expected


@pytest.mark.parametrize("option", ["--collect-only", "--co", "--help", "--ignore=tests/unit"])
def test_ci_lane_parity_rejects_pytest_nonexecuting_or_filtering_modes(
    tmp_path: Path, option: str
) -> None:
    (tmp_path / "Makefile").write_text(
        "check: unit-contract\nci: unit-contract\nci-local: unit-contract\n",
        encoding="utf-8",
    )
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "feature.yml").write_text(
        f"jobs:\n  checks:\n    steps:\n      - run: python -m pytest {option} tests/unit\n",
        encoding="utf-8",
    )
    policy = {
        "schema_version": "lotus.advise.ci-lane-parity.v1",
        "aggregate_targets": ["check", "ci", "ci-local"],
        "lanes": {"feature": ".github/workflows/feature.yml"},
        "controls": [{"target": "unit-contract", "lane_signals": {"feature": ["tests/unit"]}}],
    }

    assert evaluate(repo_root=tmp_path, policy=policy, makefile=tmp_path / "Makefile") == [
        "CI lane parity missing executable evidence for unit-contract in feature"
    ]


@pytest.mark.parametrize(
    "command",
    [
        "python -m pytest tests/integration --rootdir tests/unit",
        "python -m pytest tests/integration --ignore tests/unit",
    ],
)
def test_ci_lane_parity_requires_test_path_to_be_a_positional_collection_target(
    tmp_path: Path, command: str
) -> None:
    (tmp_path / "Makefile").write_text(
        "check: unit-contract\nci: unit-contract\nci-local: unit-contract\n",
        encoding="utf-8",
    )
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "feature.yml").write_text(
        f"jobs:\n  checks:\n    steps:\n      - run: {command}\n",
        encoding="utf-8",
    )
    policy = {
        "schema_version": "lotus.advise.ci-lane-parity.v1",
        "aggregate_targets": ["check", "ci", "ci-local"],
        "lanes": {"feature": ".github/workflows/feature.yml"},
        "controls": [{"target": "unit-contract", "lane_signals": {"feature": ["tests/unit"]}}],
    }

    assert evaluate(repo_root=tmp_path, policy=policy, makefile=tmp_path / "Makefile") == [
        "CI lane parity missing executable evidence for unit-contract in feature"
    ]


def test_ci_lane_parity_requires_matrix_path_to_be_a_positional_collection_target(
    tmp_path: Path,
) -> None:
    (tmp_path / "Makefile").write_text(
        "check: unit-contract\nci: unit-contract\nci-local: unit-contract\n",
        encoding="utf-8",
    )
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "feature.yml").write_text(
        "jobs:\n  checks:\n    strategy:\n      matrix:\n        path: tests/unit\n"
        "    steps:\n      - run: python -m pytest tests/integration --rootdir "
        "${{ matrix.path }}\n",
        encoding="utf-8",
    )
    policy = {
        "schema_version": "lotus.advise.ci-lane-parity.v1",
        "aggregate_targets": ["check", "ci", "ci-local"],
        "lanes": {"feature": ".github/workflows/feature.yml"},
        "controls": [{"target": "unit-contract", "lane_signals": {"feature": ["tests/unit"]}}],
    }

    assert evaluate(repo_root=tmp_path, policy=policy, makefile=tmp_path / "Makefile") == [
        "CI lane parity missing executable evidence for unit-contract in feature"
    ]


def test_ci_lane_parity_does_not_take_a_test_path_from_an_artifact_configuration(
    tmp_path: Path,
) -> None:
    (tmp_path / "Makefile").write_text(
        "check: unit-contract\nci: unit-contract\nci-local: unit-contract\n",
        encoding="utf-8",
    )
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "feature.yml").write_text(
        "jobs:\n  checks:\n    strategy:\n      matrix:\n        path: tests/integration\n"
        "    steps:\n      - run: python -m pytest ${{ matrix.path }}\n"
        "      - uses: actions/upload-artifact@v7\n        with:\n          path: tests/unit\n",
        encoding="utf-8",
    )
    policy = {
        "schema_version": "lotus.advise.ci-lane-parity.v1",
        "aggregate_targets": ["check", "ci", "ci-local"],
        "lanes": {"feature": ".github/workflows/feature.yml"},
        "controls": [{"target": "unit-contract", "lane_signals": {"feature": ["tests/unit"]}}],
    }

    assert evaluate(repo_root=tmp_path, policy=policy, makefile=tmp_path / "Makefile") == [
        "CI lane parity missing executable evidence for unit-contract in feature"
    ]


def test_ci_lane_parity_does_not_count_a_matrix_path_excluded_from_execution(
    tmp_path: Path,
) -> None:
    (tmp_path / "Makefile").write_text(
        "check: unit-contract\nci: unit-contract\nci-local: unit-contract\n",
        encoding="utf-8",
    )
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "feature.yml").write_text(
        "jobs:\n  checks:\n    strategy:\n      matrix:\n"
        "        path: [tests/unit, tests/integration]\n"
        "        exclude:\n          - path: tests/unit\n"
        "    steps:\n      - run: python -m pytest ${{ matrix.path }}\n",
        encoding="utf-8",
    )
    policy = {
        "schema_version": "lotus.advise.ci-lane-parity.v1",
        "aggregate_targets": ["check", "ci", "ci-local"],
        "lanes": {"feature": ".github/workflows/feature.yml"},
        "controls": [{"target": "unit-contract", "lane_signals": {"feature": ["tests/unit"]}}],
    }

    assert evaluate(repo_root=tmp_path, policy=policy, makefile=tmp_path / "Makefile") == [
        "CI lane parity missing executable evidence for unit-contract in feature"
    ]


def test_ci_lane_parity_rejects_changed_coverage_skip_receipt(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text(
        "check: changed-coverage\nci: changed-coverage\nci-local: changed-coverage\n",
        encoding="utf-8",
    )
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "feature.yml").write_text(
        "jobs:\n  checks:\n    steps:\n"
        "      - run: python scripts/changed_coverage_gate.py --policy quality/policy.json "
        "--output output/coverage.json --skip-reason unavailable\n",
        encoding="utf-8",
    )
    policy = {
        "schema_version": "lotus.advise.ci-lane-parity.v1",
        "aggregate_targets": ["check", "ci", "ci-local"],
        "lanes": {"feature": ".github/workflows/feature.yml"},
        "controls": [
            {
                "target": "changed-coverage",
                "lane_signals": {"feature": ["scripts/changed_coverage_gate.py"]},
            }
        ],
    }

    assert evaluate(repo_root=tmp_path, policy=policy, makefile=tmp_path / "Makefile") == [
        "CI lane parity missing executable evidence for changed-coverage in feature"
    ]


def test_ci_lane_parity_accepts_the_shipped_workflows_and_policy(tmp_path: Path) -> None:
    _copy_shipped_parity_inputs(tmp_path)

    assert _evaluate_shipped_inputs(tmp_path) == []


def test_ci_lane_parity_rejects_skip_reason_in_real_changed_coverage_enforcement(
    tmp_path: Path,
) -> None:
    workflows = _copy_shipped_parity_inputs(tmp_path)
    path = workflows["pr-merge-gate.yml"]
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "            --policy quality/quality-policy.v1.json \\\n"
            "            --output output/changed-coverage-gate.json\n",
            "            --policy quality/quality-policy.v1.json \\\n"
            "            --skip-reason=disabled \\\n"
            "            --output output/changed-coverage-gate.json\n",
            1,
        ),
        encoding="utf-8",
    )

    assert _evaluate_shipped_inputs(tmp_path) == [
        "CI lane parity missing executable evidence for changed-coverage-gate in pr"
    ]


@pytest.mark.parametrize(
    ("workflow", "old", "new"),
    [
        (
            "pr-merge-gate.yml",
            "  coverage-gate:\n",
            "  coverage-gate:\n    if: false\n",
        ),
        (
            "pr-merge-gate.yml",
            "        if: github.event_name == 'pull_request' || "
            "github.event_name == 'workflow_dispatch'\n",
            "        if: false\n",
        ),
        (
            "pr-merge-gate.yml",
            "        if: github.event_name == 'pull_request' || "
            "github.event_name == 'workflow_dispatch'\n",
            "        if: ${{ false && always() }}\n",
        ),
        (
            "pr-merge-gate.yml",
            "        if: github.event_name == 'pull_request' || "
            "github.event_name == 'workflow_dispatch'\n",
            "        if: ${{ false || false }}\n",
        ),
    ],
)
def test_ci_lane_parity_rejects_false_job_or_step_conditions_in_shipped_workflows(
    tmp_path: Path, workflow: str, old: str, new: str
) -> None:
    workflows = _copy_shipped_parity_inputs(tmp_path)
    path = workflows[workflow]
    path.write_text(path.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8")

    assert _evaluate_shipped_inputs(tmp_path) == [
        "CI lane parity missing executable evidence for changed-coverage-gate in pr"
    ]


@pytest.mark.parametrize(
    "replacement",
    [
        "        run: true || make quality-trend-gate",
        "        run: false && make quality-trend-gate || true",
    ],
)
def test_ci_lane_parity_rejects_short_circuited_shipped_make_controls(
    tmp_path: Path, replacement: str
) -> None:
    workflows = _copy_shipped_parity_inputs(tmp_path)
    path = workflows["feature-lane.yml"]
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "        run: make quality-trend-gate", replacement, 1
        ),
        encoding="utf-8",
    )

    assert _evaluate_shipped_inputs(tmp_path) == [
        "CI lane parity missing executable evidence for quality-trend-gate in feature"
    ]


@pytest.mark.parametrize("makeflags", ["n", "t", "q"])
def test_ci_lane_parity_rejects_nonexecuting_makeflags_in_shipped_control_context(
    tmp_path: Path, makeflags: str
) -> None:
    workflows = _copy_shipped_parity_inputs(tmp_path)
    path = workflows["feature-lane.yml"]
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "          QUALITY_HEAD_REF: HEAD\n        run: make quality-trend-gate",
            f"          QUALITY_HEAD_REF: HEAD\n          MAKEFLAGS: {makeflags}\n"
            "        run: make quality-trend-gate",
            1,
        ),
        encoding="utf-8",
    )

    assert _evaluate_shipped_inputs(tmp_path) == [
        "CI lane parity missing executable evidence for quality-trend-gate in feature"
    ]


def test_ci_lane_parity_rejects_cache_display_in_shipped_matrix_suite(tmp_path: Path) -> None:
    workflows = _copy_shipped_parity_inputs(tmp_path)
    path = workflows["pr-merge-gate.yml"]
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "        run: python -m pytest ${{ matrix.path }} --cov=src --cov-report=",
            "        run: python -m pytest --cache-show=${{ matrix.path }} "
            "${{ matrix.path }} --cov=src --cov-report=",
            1,
        ),
        encoding="utf-8",
    )

    assert _evaluate_shipped_inputs(tmp_path) == [
        "CI lane parity missing executable evidence for advisory-data-lifecycle-gate in pr",
        "CI lane parity missing executable evidence for external-adapter-contracts in pr",
    ]
