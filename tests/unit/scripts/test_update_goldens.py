import json
import shutil
import subprocess
import sys
from pathlib import Path

import update_goldens

GOLDEN_FIXTURE_DIR = Path("tests/unit/advisory/golden_data")


def _copy_fixture(tmp_path: Path, filename: str) -> Path:
    target = tmp_path / filename
    shutil.copyfile(GOLDEN_FIXTURE_DIR / filename, target)
    return target


def test_update_goldens_check_passes_for_current_proposal_fixture(tmp_path):
    _copy_fixture(tmp_path, "scenario_14A_advisory_manual_trade_cashflow.json")

    assert update_goldens.main(["--golden-dir", str(tmp_path), "--check"]) == 0


def test_update_goldens_check_passes_for_current_artifact_fixture(tmp_path):
    _copy_fixture(tmp_path, "scenario_14E_artifact_basic.json")

    assert update_goldens.main(["--golden-dir", str(tmp_path), "--check"]) == 0


def test_update_goldens_repairs_drifted_proposal_expected_output(tmp_path):
    path = _copy_fixture(tmp_path, "scenario_14A_advisory_manual_trade_cashflow.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["expected_proposal_output"]["status"] = "BLOCKED"
    path.write_text(f"{json.dumps(data, indent=2)}\n", encoding="utf-8")

    assert update_goldens.main(["--golden-dir", str(tmp_path), "--check"]) == 1
    assert update_goldens.main(["--golden-dir", str(tmp_path)]) == 0

    updated = json.loads(path.read_text(encoding="utf-8"))
    assert updated["expected_proposal_output"]["status"] == "READY"


def test_update_goldens_does_not_use_deprecated_engine_shim():
    source = Path(update_goldens.__file__).read_text(encoding="utf-8")
    assert "from src.core.engine" not in source
    assert "import src.core.engine" not in source


def test_proposal_artifact_module_imports_in_standalone_python():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from src.core.advisory.artifact import build_proposal_artifact; "
                "print(build_proposal_artifact.__name__)"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "build_proposal_artifact"
