from __future__ import annotations

from src.integrations.lotus_core.stateful_context_hydration import select_latest_dated_row


def test_select_latest_dated_row_prefers_latest_row_on_or_before_as_of() -> None:
    prior_row = {"price_date": "2026-03-25", "price": "98.50"}
    latest_eligible_row = {"price_date": "2026-03-27", "price": "99.00"}
    future_row = {"price_date": "2026-03-28", "price": "101.00"}

    assert (
        select_latest_dated_row(
            [future_row, prior_row, latest_eligible_row],
            date_key="price_date",
            as_of="2026-03-27",
        )
        is latest_eligible_row
    )


def test_select_latest_dated_row_uses_latest_future_row_when_none_are_eligible() -> None:
    first_future_row = {"rate_date": "2026-04-01", "rate": "1.09"}
    latest_future_row = {"rate_date": "2026-04-03", "rate": "1.11"}

    assert (
        select_latest_dated_row(
            [latest_future_row, first_future_row],
            date_key="rate_date",
            as_of="2026-03-27",
        )
        is latest_future_row
    )


def test_select_latest_dated_row_rejects_malformed_or_undated_rows() -> None:
    dated_row = {"price_date": "2026-03-27", "price": "99.00"}

    assert (
        select_latest_dated_row(
            [
                "bad-row",
                {"price_date": None, "price": "98.00"},
                {"price_date": 20260327, "price": "98.50"},
                {"price": "97.00"},
                dated_row,
            ],
            date_key="price_date",
            as_of="2026-03-27",
        )
        is dated_row
    )
    assert select_latest_dated_row([], date_key="price_date", as_of="2026-03-27") is None
