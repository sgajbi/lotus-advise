from __future__ import annotations

from datetime import datetime, timedelta


def retention_expires_at(*, retention_class: str, created_at: datetime) -> datetime:
    if retention_class == "SUPPORTABILITY_DIAGNOSTIC":
        return created_at + timedelta(days=90)
    return created_at + timedelta(days=365 * 7)
