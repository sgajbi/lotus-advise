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


def extract_live_proposal_alternatives_snapshot(
    proposal_body: Mapping[str, Any],
    *,
    path_name: str,
    latency_ms: float,
) -> LiveProposalAlternativesSnapshot:
    alternatives = proposal_body.get("proposal_alternatives")
    if not isinstance(alternatives, Mapping):
        raise ValueError(f"{path_name}: proposal_alternatives missing from response body")

    requested_objectives = alternatives.get("requested_objectives")
    if not isinstance(requested_objectives, list):
        raise ValueError(f"{path_name}: requested_objectives missing from proposal_alternatives")

    ranked_alternatives = alternatives.get("alternatives")
    if not isinstance(ranked_alternatives, list):
        raise ValueError(f"{path_name}: alternatives missing from proposal_alternatives")

    rejected_candidates = alternatives.get("rejected_candidates")
    if not isinstance(rejected_candidates, list):
        raise ValueError(f"{path_name}: rejected_candidates missing from proposal_alternatives")

    feasible_count = 0
    feasible_with_review_count = 0
    selected_alternative_id: str | None = None
    selected_rank: int | None = None
    top_ranked_alternative_id: str | None = None
    top_ranked_objective: str | None = None
    top_ranked_reason_codes: tuple[str, ...] = ()

    for alternative in ranked_alternatives:
        if not isinstance(alternative, Mapping):
            continue
        status = str(alternative.get("status") or "")
        if status == "FEASIBLE":
            feasible_count += 1
        elif status == "FEASIBLE_WITH_REVIEW":
            feasible_with_review_count += 1

        if alternative.get("selected") is True:
            selected_alternative_id = _optional_string(alternative.get("alternative_id"))
            selected_rank = _optional_int(alternative.get("rank"))

        rank = _optional_int(alternative.get("rank"))
        if rank == 1 and top_ranked_alternative_id is None:
            top_ranked_alternative_id = _optional_string(alternative.get("alternative_id"))
            top_ranked_objective = _optional_string(alternative.get("objective"))
            ranking_projection = alternative.get("ranking_projection")
            if isinstance(ranking_projection, Mapping):
                reason_codes = ranking_projection.get("ranking_reason_codes")
                if isinstance(reason_codes, list):
                    top_ranked_reason_codes = tuple(
                        str(item) for item in reason_codes if str(item).strip()
                    )

    explicit_selected_alternative_id = _optional_string(alternatives.get("selected_alternative_id"))
    if selected_alternative_id is None:
        selected_alternative_id = explicit_selected_alternative_id

    rejected_reason_codes = tuple(
        sorted(
            str(candidate.get("reason_code"))
            for candidate in rejected_candidates
            if isinstance(candidate, Mapping) and str(candidate.get("reason_code") or "").strip()
        )
    )

    return LiveProposalAlternativesSnapshot(
        path_name=path_name,
        requested_objectives=tuple(str(item) for item in requested_objectives if str(item).strip()),
        feasible_count=feasible_count,
        feasible_with_review_count=feasible_with_review_count,
        rejected_count=len(rejected_candidates),
        selected_alternative_id=selected_alternative_id,
        selected_rank=selected_rank,
        top_ranked_alternative_id=top_ranked_alternative_id,
        top_ranked_objective=top_ranked_objective,
        top_ranked_reason_codes=top_ranked_reason_codes,
        rejected_reason_codes=rejected_reason_codes,
        latency_ms=latency_ms,
    )


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
