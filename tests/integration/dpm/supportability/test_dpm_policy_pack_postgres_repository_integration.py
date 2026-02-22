import os
import uuid
from contextlib import closing

import pytest

from src.core.dpm.policy_packs import DpmPolicyPackDefinition
from src.infrastructure.dpm_policy_packs.postgres import PostgresDpmPolicyPackRepository
from tests.unit.dpm.supportability.test_dpm_policy_pack_postgres_repository import (
    _build_repository as _build_fake_repository,
)

_DSN = os.getenv("DPM_POSTGRES_INTEGRATION_DSN", "").strip()


@pytest.fixture
def repository(monkeypatch: pytest.MonkeyPatch) -> PostgresDpmPolicyPackRepository:
    if _DSN:
        try:
            repo = PostgresDpmPolicyPackRepository(dsn=_DSN)
            _reset_tables(repo)
            return repo
        except Exception:
            pass
    repo, _ = _build_fake_repository(monkeypatch)
    return repo


def test_live_postgres_policy_pack_repository_roundtrip(
    repository: PostgresDpmPolicyPackRepository,
) -> None:
    policy_pack_id = f"pp-{uuid.uuid4().hex[:12]}"
    updated_policy_pack_id = f"{policy_pack_id}-updated"
    policy_pack = DpmPolicyPackDefinition(
        policy_pack_id=policy_pack_id,
        version="1",
    )
    repository.upsert_policy_pack(policy_pack)

    loaded = repository.get_policy_pack(policy_pack_id=policy_pack_id)
    assert loaded is not None
    assert loaded.policy_pack_id == policy_pack_id
    assert loaded.version == "1"

    listed = repository.list_policy_packs()
    assert [row.policy_pack_id for row in listed] == [policy_pack_id]

    repository.upsert_policy_pack(
        DpmPolicyPackDefinition(
            policy_pack_id=policy_pack_id,
            version="2",
        )
    )
    loaded_after_update = repository.get_policy_pack(policy_pack_id=policy_pack_id)
    assert loaded_after_update is not None
    assert loaded_after_update.version == "2"

    repository.upsert_policy_pack(
        DpmPolicyPackDefinition(
            policy_pack_id=updated_policy_pack_id,
            version="1",
        )
    )
    listed_two = repository.list_policy_packs()
    assert sorted(row.policy_pack_id for row in listed_two) == sorted(
        [policy_pack_id, updated_policy_pack_id]
    )

    assert repository.delete_policy_pack(policy_pack_id=policy_pack_id) is True
    assert repository.delete_policy_pack(policy_pack_id=policy_pack_id) is False
    assert repository.get_policy_pack(policy_pack_id=policy_pack_id) is None


def _reset_tables(repository: PostgresDpmPolicyPackRepository) -> None:
    with closing(repository._connect()) as connection:  # noqa: SLF001
        connection.execute("DELETE FROM dpm_policy_packs")
        connection.commit()
