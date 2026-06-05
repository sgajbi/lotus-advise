from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RadonComplexitySummary:
    block_count: int
    rank_counts: dict[str, int]
    worst_rank: str | None
    worst_complexity: int | None
    failing_blocks: tuple[str, ...]


def parse_radon_report(payload_text: str, *, fail_rank: str = "F") -> RadonComplexitySummary:
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Radon did not return valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Radon JSON payload must be an object.")

    rank_order = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}
    fail_threshold = rank_order.get(fail_rank.upper())
    if fail_threshold is None:
        raise ValueError(f"Unsupported Radon fail rank: {fail_rank}.")

    blocks: list[dict[str, object]] = []

    def collect(block: object, file_path: str) -> None:
        if not isinstance(block, dict):
            raise ValueError("Radon block entries must be objects.")
        block["_file_path"] = file_path
        blocks.append(block)
        for child_key in ("methods", "closures"):
            children = block.get(child_key)
            if isinstance(children, list):
                for child in children:
                    collect(child, file_path)

    for file_path, file_blocks in payload.items():
        if not isinstance(file_path, str) or not isinstance(file_blocks, list):
            raise ValueError("Radon JSON payload must map files to block arrays.")
        for block in file_blocks:
            collect(block, file_path)

    rank_counts = Counter(
        str(block.get("rank")).upper()
        for block in blocks
        if isinstance(block.get("rank"), str) and str(block.get("rank")).upper() in rank_order
    )
    worst_block = max(
        blocks,
        key=lambda block: (
            int(block.get("complexity", 0)) if isinstance(block.get("complexity"), int) else 0
        ),
        default=None,
    )
    failing_blocks = tuple(
        _format_block(block)
        for block in blocks
        if rank_order.get(str(block.get("rank")).upper(), 0) >= fail_threshold
    )
    return RadonComplexitySummary(
        block_count=len(blocks),
        rank_counts=dict(sorted(rank_counts.items())),
        worst_rank=str(worst_block.get("rank")).upper() if worst_block else None,
        worst_complexity=int(worst_block.get("complexity", 0)) if worst_block else None,
        failing_blocks=failing_blocks,
    )


def _format_block(block: dict[str, object]) -> str:
    file_path = str(block.get("_file_path", "unknown"))
    name = str(block.get("name", "unknown"))
    rank = str(block.get("rank", "unknown")).upper()
    complexity = block.get("complexity", "unknown")
    return f"{file_path}:{name}: rank={rank}, complexity={complexity}"


def run_radon(repo_root: Path, source_path: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "radon", "cc", source_path, "-s", "-j"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail when Radon reports complexity blocks at or above a configured rank."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root for Radon execution.",
    )
    parser.add_argument("--source-path", default="src", help="Path to scan from the repo root.")
    parser.add_argument(
        "--fail-rank",
        default="F",
        choices=("A", "B", "C", "D", "E", "F"),
        help="Fail when any block has this rank or worse.",
    )
    args = parser.parse_args(argv)

    completed = run_radon(args.repo_root.resolve(), args.source_path)
    if completed.returncode != 0:
        print(completed.stderr.strip() or "Radon execution failed.", file=sys.stderr)
        return 1

    try:
        summary = parse_radon_report(completed.stdout, fail_rank=args.fail_rank)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    rank_inventory = (
        ", ".join(f"{rank}={count}" for rank, count in summary.rank_counts.items()) or "none"
    )
    print(
        "Radon complexity gate: "
        f"blocks={summary.block_count}, ranks={rank_inventory}, "
        f"worst={summary.worst_rank}/{summary.worst_complexity}, fail_rank={args.fail_rank}"
    )
    if summary.failing_blocks:
        print("Radon complexity gate failed.", file=sys.stderr)
        for block in summary.failing_blocks[:10]:
            print(f"- {block}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
