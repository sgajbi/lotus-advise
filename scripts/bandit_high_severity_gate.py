from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

BASELINE_SCHEMA_VERSION = "lotus.bandit-security-baseline.v1"
DEFAULT_BASELINE_PATH = Path("quality/bandit_security_baseline.v1.json")
DEFAULT_REMEDIATION_URL = "https://github.com/sgajbi/lotus-advise/issues/435"

SEVERITY_ORDER = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
}


@dataclass(frozen=True)
class BanditSeveritySummary:
    issue_count: int
    high_count: int
    medium_count: int
    low_count: int


@dataclass(frozen=True)
class BanditFinding:
    fingerprint: str
    test_id: str
    test_name: str
    severity: str
    confidence: str
    filename: str
    line_number: int
    issue_text: str


@dataclass(frozen=True)
class BanditBaselineEntry:
    fingerprint: str
    test_id: str
    severity: str
    confidence: str
    filename: str
    line_number: int
    owner: str
    rationale: str
    expires_on: date
    linked_remediation: str
    compensating_control: str


def parse_bandit_report(payload_text: str) -> BanditSeveritySummary:
    results = _load_bandit_results(payload_text)
    severities: Counter[str] = Counter()
    for result in results:
        severity = result.get("issue_severity")
        if isinstance(severity, str):
            severities[severity.upper()] += 1

    return BanditSeveritySummary(
        issue_count=len(results),
        high_count=severities["HIGH"],
        medium_count=severities["MEDIUM"],
        low_count=severities["LOW"],
    )


def parse_bandit_findings(payload_text: str) -> list[BanditFinding]:
    return [_finding_from_result(result) for result in _load_bandit_results(payload_text)]


def validate_bandit_report_against_baseline(
    payload_text: str,
    baseline_path: Path,
    *,
    today: date | None = None,
) -> tuple[BanditSeveritySummary, list[str]]:
    summary = parse_bandit_report(payload_text)
    findings = parse_bandit_findings(payload_text)
    effective_today = today or date.today()
    baseline_entries, baseline_failures = load_bandit_baseline(baseline_path, today=effective_today)

    failures = list(baseline_failures)
    current_by_fingerprint: dict[str, BanditFinding] = {}
    for finding in findings:
        if finding.fingerprint in current_by_fingerprint:
            failures.append(
                f"Duplicate Bandit finding fingerprint {finding.fingerprint} in current report."
            )
        current_by_fingerprint[finding.fingerprint] = finding

    baseline_by_fingerprint: dict[str, BanditBaselineEntry] = {}
    for entry in baseline_entries:
        if entry.fingerprint in baseline_by_fingerprint:
            failures.append(f"Duplicate Bandit baseline fingerprint {entry.fingerprint}.")
        baseline_by_fingerprint[entry.fingerprint] = entry

    for finding in findings:
        if finding.severity == "HIGH":
            failures.append(
                f"Bandit high-severity finding is never baselined: "
                f"{finding.test_id} {finding.filename}:{finding.line_number}"
            )
            continue
        entry = baseline_by_fingerprint.get(finding.fingerprint)
        if entry is None:
            failures.append(
                f"New Bandit {finding.severity} finding {finding.test_id} "
                f"{finding.filename}:{finding.line_number} fingerprint={finding.fingerprint}"
            )
            continue
        if SEVERITY_ORDER[finding.severity] > SEVERITY_ORDER[entry.severity]:
            failures.append(
                f"Bandit severity increased for {finding.fingerprint}: "
                f"baseline={entry.severity}, current={finding.severity}"
            )

    for fingerprint, entry in baseline_by_fingerprint.items():
        if fingerprint not in current_by_fingerprint:
            failures.append(
                f"Stale Bandit baseline entry {fingerprint} no longer appears in the report; "
                f"remove or renew {entry.filename}:{entry.line_number}."
            )

    return summary, failures


def load_bandit_baseline(
    baseline_path: Path,
    *,
    today: date | None = None,
) -> tuple[list[BanditBaselineEntry], list[str]]:
    if not baseline_path.exists():
        return [], [f"Bandit baseline file is missing: {baseline_path.as_posix()}"]

    effective_today = today or date.today()
    try:
        payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], [f"Bandit baseline is not valid JSON: {exc}"]

    failures: list[str] = []
    if not isinstance(payload, dict):
        return [], ["Bandit baseline JSON payload must be an object."]
    if payload.get("schema_version") != BASELINE_SCHEMA_VERSION:
        failures.append(f"Bandit baseline schema_version must be {BASELINE_SCHEMA_VERSION!r}.")
    entries_payload = payload.get("entries")
    if not isinstance(entries_payload, list):
        return [], failures + ["Bandit baseline entries must be a list."]

    entries: list[BanditBaselineEntry] = []
    for index, raw_entry in enumerate(entries_payload):
        if not isinstance(raw_entry, dict):
            failures.append(f"Bandit baseline entry {index} must be an object.")
            continue
        entry, entry_failures = _load_baseline_entry(raw_entry, index, effective_today)
        failures.extend(entry_failures)
        if entry is not None:
            entries.append(entry)
    return entries, failures


def build_current_baseline_payload(
    payload_text: str,
    *,
    owner: str,
    rationale: str,
    expires_on: date,
    linked_remediation: str,
    compensating_control: str,
) -> dict[str, Any]:
    findings = sorted(
        parse_bandit_findings(payload_text),
        key=lambda finding: (finding.filename, finding.line_number, finding.test_id),
    )
    entries = []
    for finding in findings:
        if finding.severity == "HIGH":
            continue
        entries.append(
            {
                "fingerprint": finding.fingerprint,
                "test_id": finding.test_id,
                "test_name": finding.test_name,
                "severity": finding.severity,
                "confidence": finding.confidence,
                "filename": finding.filename,
                "line_number": finding.line_number,
                "owner": owner,
                "rationale": rationale,
                "expires_on": expires_on.isoformat(),
                "linked_remediation": linked_remediation,
                "compensating_control": compensating_control,
            }
        )
    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "service": "lotus-advise",
        "source_path": "src",
        "entries": entries,
    }


def write_current_baseline(
    payload_text: str,
    baseline_path: Path,
    *,
    owner: str,
    rationale: str,
    expires_on: date,
    linked_remediation: str,
    compensating_control: str,
) -> None:
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_current_baseline_payload(
        payload_text,
        owner=owner,
        rationale=rationale,
        expires_on=expires_on,
        linked_remediation=linked_remediation,
        compensating_control=compensating_control,
    )
    baseline_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_bandit_results(payload_text: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Bandit did not return valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Bandit JSON payload must be an object.")
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("Bandit JSON payload is missing a results array.")
    for result in results:
        if not isinstance(result, dict):
            raise ValueError("Bandit result entries must be objects.")
    return results


def _finding_from_result(result: dict[str, Any]) -> BanditFinding:
    severity = _normalize_severity(result.get("issue_severity"))
    confidence = _normalize_confidence(result.get("issue_confidence"))
    filename = str(result.get("filename", "")).replace("\\", "/")
    line_number = int(result.get("line_number") or 0)
    issue_text = str(result.get("issue_text", ""))
    test_id = str(result.get("test_id", ""))
    test_name = str(result.get("test_name", ""))
    code = _normalize_code(str(result.get("code", "")))
    fingerprint_payload = {
        "code": code,
        "filename": filename,
        "issue_text": issue_text,
        "test_id": test_id,
        "test_name": test_name,
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return BanditFinding(
        fingerprint=fingerprint,
        test_id=test_id,
        test_name=test_name,
        severity=severity,
        confidence=confidence,
        filename=filename,
        line_number=line_number,
        issue_text=issue_text,
    )


def _load_baseline_entry(
    raw_entry: dict[str, Any],
    index: int,
    today: date,
) -> tuple[BanditBaselineEntry | None, list[str]]:
    failures: list[str] = []
    required_fields = (
        "fingerprint",
        "test_id",
        "severity",
        "confidence",
        "filename",
        "line_number",
        "owner",
        "rationale",
        "expires_on",
        "linked_remediation",
        "compensating_control",
    )
    for field in required_fields:
        value = raw_entry.get(field)
        if value in (None, ""):
            failures.append(f"Bandit baseline entry {index} missing {field}.")

    try:
        severity = _normalize_severity(raw_entry.get("severity"))
    except ValueError:
        failures.append(f"Bandit baseline entry {index} has invalid severity.")
        severity = "LOW"
    try:
        confidence = _normalize_confidence(raw_entry.get("confidence"))
    except ValueError:
        failures.append(f"Bandit baseline entry {index} has invalid confidence.")
        confidence = "LOW"
    try:
        expires_on = date.fromisoformat(str(raw_entry.get("expires_on")))
    except ValueError:
        failures.append(f"Bandit baseline entry {index} has invalid expires_on.")
        expires_on = today
    if expires_on < today:
        failures.append(f"Bandit baseline entry {index} expired on {expires_on.isoformat()}.")
    if failures:
        return None, failures
    return (
        BanditBaselineEntry(
            fingerprint=str(raw_entry["fingerprint"]),
            test_id=str(raw_entry["test_id"]),
            severity=severity,
            confidence=confidence,
            filename=str(raw_entry["filename"]),
            line_number=int(raw_entry["line_number"]),
            owner=str(raw_entry["owner"]),
            rationale=str(raw_entry["rationale"]),
            expires_on=expires_on,
            linked_remediation=str(raw_entry["linked_remediation"]),
            compensating_control=str(raw_entry["compensating_control"]),
        ),
        [],
    )


def _normalize_severity(raw_severity: object) -> str:
    severity = str(raw_severity or "").upper()
    if severity not in SEVERITY_ORDER:
        raise ValueError(f"Unsupported Bandit severity: {raw_severity!r}")
    return severity


def _normalize_confidence(raw_confidence: object) -> str:
    confidence = str(raw_confidence or "").upper()
    if confidence not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError(f"Unsupported Bandit confidence: {raw_confidence!r}")
    return confidence


def _normalize_code(code: str) -> str:
    normalized_lines = []
    for line in code.splitlines():
        stripped = line.strip()
        parts = stripped.split(maxsplit=1)
        normalized_lines.append(
            parts[1] if parts and parts[0].isdigit() and len(parts) > 1 else stripped
        )
    return "\n".join(normalized_lines)


def run_bandit(
    repo_root: Path,
    source_path: str,
    config_path: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "bandit",
            "-q",
            "-r",
            source_path,
            "-c",
            config_path,
            "-f",
            "json",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail when Bandit reports high, new, or worsened security findings."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root containing the Bandit configuration.",
    )
    parser.add_argument("--source-path", default="src", help="Path to scan from the repo root.")
    parser.add_argument(
        "--config",
        default="pyproject.toml",
        help="Bandit configuration path relative to the repo root.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
        help="Governed Bandit medium/low baseline path relative to the repo root.",
    )
    parser.add_argument(
        "--write-current-baseline",
        action="store_true",
        help="Write a baseline from the current Bandit report instead of validating it.",
    )
    parser.add_argument("--baseline-owner", default="lotus-advise-security")
    parser.add_argument(
        "--baseline-rationale",
        default=(
            "Current Bandit medium/low inventory accepted as non-certifying baseline while "
            "constant-owned SQL templates are reviewed for narrower query-builder patterns."
        ),
    )
    parser.add_argument("--baseline-expires-on", default="2026-12-31")
    parser.add_argument("--baseline-remediation", default=DEFAULT_REMEDIATION_URL)
    parser.add_argument(
        "--baseline-compensating-control",
        default=(
            "CI blocks high findings plus any new, stale, expired, or worsened medium/low "
            "finding; PostgreSQL values remain parameterized."
        ),
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    completed = run_bandit(repo_root, args.source_path, args.config)
    if completed.returncode not in {0, 1}:
        print(completed.stderr.strip() or "Bandit execution failed.", file=sys.stderr)
        return 1
    if not completed.stdout.strip():
        print(completed.stderr.strip() or "Bandit did not return a report.", file=sys.stderr)
        return 1

    try:
        expires_on = date.fromisoformat(args.baseline_expires_on)
        baseline_path = args.baseline
        if not baseline_path.is_absolute():
            baseline_path = repo_root / baseline_path
        if args.write_current_baseline:
            write_current_baseline(
                completed.stdout,
                baseline_path,
                owner=args.baseline_owner,
                rationale=args.baseline_rationale,
                expires_on=expires_on,
                linked_remediation=args.baseline_remediation,
                compensating_control=args.baseline_compensating_control,
            )
            summary = parse_bandit_report(completed.stdout)
            failures: list[str] = []
        else:
            summary, failures = validate_bandit_report_against_baseline(
                completed.stdout,
                baseline_path,
            )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        "Bandit severity-regression gate: "
        f"high={summary.high_count}, medium={summary.medium_count}, "
        f"low={summary.low_count}, total={summary.issue_count}"
    )
    for failure in failures:
        print(failure, file=sys.stderr)
    if failures:
        print("Bandit severity-regression gate failed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
