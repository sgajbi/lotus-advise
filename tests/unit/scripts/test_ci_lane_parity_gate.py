import json
from pathlib import Path

from scripts.ci_lane_parity_gate import evaluate, load_policy


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
        "feature.yml": "run: python scripts/direct.py\nrun: python -m pytest tests/unit\n",
        "pr.yml": "run: python scripts/direct.py\nrun: python scripts/changed.py\n",
        "main.yml": "run: python -m pytest tests/unit\nrun: python scripts/changed.py\n",
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
