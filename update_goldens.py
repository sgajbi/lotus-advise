"""Regenerate or verify advisory golden data files.

The golden fixtures intentionally store focused expected-output slices instead of full engine
responses. This helper keeps those slices aligned with the current proposal simulation and
proposal-artifact code paths without broadening the fixture contract by accident.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Sequence

from src.core.advisory_engine import run_proposal_simulation
from src.core.models import ProposalResult, ProposalSimulateRequest

GOLDEN_DIR = Path("tests/unit/advisory/golden_data")


def _decimal_encoder(obj: object) -> str:
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _load_golden(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)


def _write_golden(path: Path, data: dict[str, Any]) -> None:
    payload = json.dumps(data, indent=2, default=_decimal_encoder)
    path.write_text(f"{payload}\n", encoding="utf-8")


def _looks_decimal(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        Decimal(value)
    except InvalidOperation:
        return False
    return True


def _match_decimal_scale(actual: object, template: str) -> str:
    actual_decimal = Decimal(str(actual))
    template_decimal = Decimal(template)
    return format(actual_decimal.quantize(template_decimal), "f")


def _project_to_template(actual: Any, template: Any) -> Any:
    if isinstance(template, dict):
        if not isinstance(actual, dict):
            raise ValueError(f"Expected mapping while projecting {template!r}")
        return {key: _project_to_template(actual[key], value) for key, value in template.items()}
    if isinstance(template, list):
        if not isinstance(actual, list):
            raise ValueError(f"Expected list while projecting {template!r}")
        return [
            _project_to_template(actual_item, template_item)
            for actual_item, template_item in zip(actual, template, strict=True)
        ]
    if _looks_decimal(template):
        return _match_decimal_scale(actual, template)
    return actual


def _run_proposal(path: Path, request: ProposalSimulateRequest) -> ProposalResult:
    scenario_id = path.stem
    return run_proposal_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        shelf=request.shelf_entries,
        options=request.options,
        proposed_cash_flows=request.proposed_cash_flows,
        proposed_trades=request.proposed_trades,
        reference_model=request.reference_model,
        request_hash=f"sha256:golden-{scenario_id}",
        idempotency_key=f"golden-{scenario_id}",
        correlation_id=f"corr-{scenario_id}",
    )


def _proposal_expected_output(
    *,
    current_expected: dict[str, Any],
    proposal_result: ProposalResult,
) -> dict[str, Any]:
    result_dump = proposal_result.model_dump(mode="json")
    diagnostics_dump = proposal_result.diagnostics.model_dump(mode="json")
    generated: dict[str, Any] = {}

    for key, template in current_expected.items():
        if key in {"missing_fx_pairs", "funding_plan", "insufficient_cash"}:
            generated[key] = _project_to_template(diagnostics_dump[key], template)
            continue
        generated[key] = _project_to_template(result_dump[key], template)

    return generated


def _artifact_expected_output(
    *,
    current_expected: dict[str, Any],
    proposal_result: ProposalResult,
    request: ProposalSimulateRequest,
) -> dict[str, Any]:
    from src.core.advisory.artifact import build_proposal_artifact

    artifact = build_proposal_artifact(request=request, proposal_result=proposal_result)
    values_by_key: dict[str, Any] = {
        "status": artifact.status,
        "recommended_next_step": artifact.summary.recommended_next_step,
        "objective_tags": artifact.summary.objective_tags,
        "trade_instruments": [
            trade.instrument_id for trade in artifact.trades_and_funding.trade_list
        ],
        "fx_pairs": [fx.pair for fx in artifact.trades_and_funding.fx_list],
        "suitability_status": artifact.suitability_summary.status,
    }
    return {
        key: _project_to_template(values_by_key[key], template)
        for key, template in current_expected.items()
    }


def regenerate_golden_document(path: Path) -> dict[str, Any]:
    data = _load_golden(path)
    request = ProposalSimulateRequest.model_validate(data["proposal_inputs"])
    proposal_result = _run_proposal(path, request)

    if "expected_proposal_output" in data:
        data["expected_proposal_output"] = _proposal_expected_output(
            current_expected=data["expected_proposal_output"],
            proposal_result=proposal_result,
        )
        return data

    if "expected_artifact_output" in data:
        data["expected_artifact_output"] = _artifact_expected_output(
            current_expected=data["expected_artifact_output"],
            proposal_result=proposal_result,
            request=request,
        )
        return data

    raise ValueError(
        f"{path} is not a supported advisory golden fixture: expected one of "
        "expected_proposal_output or expected_artifact_output"
    )


def update_golden_file(path: Path, *, check: bool) -> bool:
    original = _load_golden(path)
    updated = regenerate_golden_document(path)
    if updated == original:
        return False
    if not check:
        _write_golden(path, updated)
    return True


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate or verify advisory proposal golden fixtures."
    )
    parser.add_argument(
        "--golden-dir",
        type=Path,
        default=GOLDEN_DIR,
        help=f"Directory containing advisory golden JSON fixtures. Defaults to {GOLDEN_DIR}.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if committed golden fixtures do not match regenerated expected outputs.",
    )
    args = parser.parse_args(argv)

    files = sorted(args.golden_dir.glob("*.json"))
    if not files:
        print(f"No advisory golden fixtures found in {args.golden_dir}.")
        return 1

    drifted: list[Path] = []
    for path in files:
        if update_golden_file(path, check=args.check):
            drifted.append(path)

    if args.check and drifted:
        print("Golden fixture drift detected:")
        for path in drifted:
            print(f"  - {path}")
        return 1

    action = "checked" if args.check else "updated"
    print(f"Advisory golden fixtures {action}: {len(files)} file(s), {len(drifted)} changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
