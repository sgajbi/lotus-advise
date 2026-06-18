from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class LiveProposalAlternativesSnapshot:
    path_name: str
    requested_objectives: tuple[str, ...]
    feasible_count: int
    feasible_with_review_count: int
    rejected_count: int
    selected_alternative_id: str | None
    selected_rank: int | None
    top_ranked_alternative_id: str | None
    top_ranked_objective: str | None
    top_ranked_reason_codes: tuple[str, ...]
    rejected_reason_codes: tuple[str, ...]
    latency_ms: float


@dataclass(frozen=True)
class _RankedAlternativesSummary:
    feasible_count: int
    feasible_with_review_count: int
    selected_alternative_id: str | None
    selected_rank: int | None
    top_ranked_alternative_id: str | None
    top_ranked_objective: str | None
    top_ranked_reason_codes: tuple[str, ...]


def extract_live_proposal_alternatives_snapshot(
    proposal_body: Mapping[str, Any],
    *,
    path_name: str,
    latency_ms: float,
) -> LiveProposalAlternativesSnapshot:
    alternatives = _required_mapping(
        proposal_body.get("proposal_alternatives"),
        path_name=path_name,
        field_name="proposal_alternatives",
        parent_name="response body",
    )
    requested_objectives = _required_list(
        alternatives.get("requested_objectives"),
        path_name=path_name,
        field_name="requested_objectives",
    )
    ranked_alternatives = _required_list(
        alternatives.get("alternatives"),
        path_name=path_name,
        field_name="alternatives",
    )
    rejected_candidates = _required_list(
        alternatives.get("rejected_candidates"),
        path_name=path_name,
        field_name="rejected_candidates",
    )

    ranked_summary = _summarize_ranked_alternatives(ranked_alternatives)
    selected_alternative_id = ranked_summary.selected_alternative_id or _optional_string(
        alternatives.get("selected_alternative_id")
    )

    return LiveProposalAlternativesSnapshot(
        path_name=path_name,
        requested_objectives=_non_empty_strings(requested_objectives),
        feasible_count=ranked_summary.feasible_count,
        feasible_with_review_count=ranked_summary.feasible_with_review_count,
        rejected_count=len(rejected_candidates),
        selected_alternative_id=selected_alternative_id,
        selected_rank=ranked_summary.selected_rank,
        top_ranked_alternative_id=ranked_summary.top_ranked_alternative_id,
        top_ranked_objective=ranked_summary.top_ranked_objective,
        top_ranked_reason_codes=ranked_summary.top_ranked_reason_codes,
        rejected_reason_codes=_rejected_reason_codes(rejected_candidates),
        latency_ms=latency_ms,
    )


def _required_mapping(
    value: Any,
    *,
    path_name: str,
    field_name: str,
    parent_name: str,
) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    raise ValueError(f"{path_name}: {field_name} missing from {parent_name}")


def _required_list(
    value: Any,
    *,
    path_name: str,
    field_name: str,
) -> list[Any]:
    if isinstance(value, list):
        return value
    raise ValueError(f"{path_name}: {field_name} missing from proposal_alternatives")


def _summarize_ranked_alternatives(
    ranked_alternatives: list[Any],
) -> _RankedAlternativesSummary:
    feasible_count = 0
    feasible_with_review_count = 0
    selected_alternative_id: str | None = None
    selected_rank: int | None = None
    top_ranked: Mapping[str, Any] | None = None

    for alternative in ranked_alternatives:
        if not isinstance(alternative, Mapping):
            continue
        status = str(alternative.get("status") or "")
        feasible_count += int(status == "FEASIBLE")
        feasible_with_review_count += int(status == "FEASIBLE_WITH_REVIEW")

        if alternative.get("selected") is True:
            selected_alternative_id = _optional_string(alternative.get("alternative_id"))
            selected_rank = _optional_int(alternative.get("rank"))

        if _optional_int(alternative.get("rank")) == 1 and top_ranked is None:
            top_ranked = alternative

    top_ranked_summary = _top_ranked_summary(top_ranked)
    return _RankedAlternativesSummary(
        feasible_count=feasible_count,
        feasible_with_review_count=feasible_with_review_count,
        selected_alternative_id=selected_alternative_id,
        selected_rank=selected_rank,
        top_ranked_alternative_id=top_ranked_summary[0],
        top_ranked_objective=top_ranked_summary[1],
        top_ranked_reason_codes=top_ranked_summary[2],
    )


def _top_ranked_summary(
    alternative: Mapping[str, Any] | None,
) -> tuple[str | None, str | None, tuple[str, ...]]:
    if alternative is None:
        return None, None, ()
    return (
        _optional_string(alternative.get("alternative_id")),
        _optional_string(alternative.get("objective")),
        _ranking_reason_codes(alternative.get("ranking_projection")),
    )


def _ranking_reason_codes(ranking_projection: Any) -> tuple[str, ...]:
    if not isinstance(ranking_projection, Mapping):
        return ()
    reason_codes = ranking_projection.get("ranking_reason_codes")
    if not isinstance(reason_codes, list):
        return ()
    return _non_empty_strings(reason_codes)


def _rejected_reason_codes(rejected_candidates: list[Any]) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(candidate.get("reason_code"))
            for candidate in rejected_candidates
            if isinstance(candidate, Mapping) and str(candidate.get("reason_code") or "").strip()
        )
    )


def _non_empty_strings(values: list[Any]) -> tuple[str, ...]:
    return tuple(str(item) for item in values if str(item).strip())


def _optional_string(value: Any) -> str | None:
    normalized = str(value).strip() if value is not None else ""
    return normalized or None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
