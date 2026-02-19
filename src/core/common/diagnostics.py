"""
Shared diagnostics builders for engine pipelines.
"""

from src.core.models import DiagnosticsData


def make_empty_data_quality_log():
    return {"price_missing": [], "fx_missing": [], "shelf_missing": []}


def make_diagnostics_data():
    return DiagnosticsData(
        warnings=[],
        suppressed_intents=[],
        group_constraint_events=[],
        data_quality=make_empty_data_quality_log(),
    )
